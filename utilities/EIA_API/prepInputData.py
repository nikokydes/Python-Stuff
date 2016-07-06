import sys
import os
import json
import csv
from collections import Counter
import urllib2
import zipfile
import optparse
import string
import itertools
import math
from datetime import datetime, timedelta
from calendar import monthrange
# import datetime

# The 'xlrd' package to handle reading from Excel files must be installed
#  separately.    
# To install:
#    1. Open a cmd window and cd to the 'Scripts' directory of your Python installation (i.e. C:\Python27\Scripts)
#    2. Type "easy_install.exe xlrd" and hit Enter
import xlrd

# The 'Shapely' and 'Fiona' packages for spatial geometry need to be installed separately
# To install:
#    1. Open a cmd window and cd to the 'Scripts' directory of your Python installation (i.e. C:\Python27\Scripts)
#    2. Download the 'Shapely*.whl' and 'Fiona*.whl' and GDAL*.whl windows installation files (Google is your friend..)
#    3. Type 'pip install <file>.whl for each installation <file> you have downloaded'
import fiona
from shapely.geometry import shape, Point


#####################################################################
# Subtract a specified number of months from a date
#####################################################################
def substractMonths(d,numMonths):
  startMonth = int(str(d)[4:6])
  startYear  = int(str(d)[0:4])

  ys = numMonths // 12
  ms = numMonths % 12
  if ms >= startMonth:
    ys += 1
    return int(str(startYear-ys)+str(12-ms+startMonth).zfill(2))
  else:
    return int(str(startYear-ys)+str(startMonth-ms).zfill(2))

#####################################################################
# Find element in list for which percentile % are smaller
#####################################################################
def percentile(data, percentile):
  size = len(data)
  return sorted(data)[int(math.ceil((size * percentile) / 100)) - 1]        
 


#####################################################################
# Download bulk JSON API files from EIA website
#####################################################################
def pullAPIdata():
    print 'Retrieving bulk API data from EIA website...'

    bulk_API_zips=['PET.zip',
                   'STEO.zip',
                   'SEDS.zip']

    for file in bulk_API_zips:
      print "...Downloading " + file 
      try:
        response = urllib2.urlopen("http://api.eia.gov/bulk/"+file)
        content = response.read()
        f = open( file, 'wb' )
        f.write( content )
        f.close()

        filebase = file.split('.')[0].strip()
        if os.path.isfile(file):
          with zipfile.ZipFile(file, "r") as z:
            z.extractall()
          if os.path.isfile(filebase+".json"):
            os.remove(filebase+".json") 
          os.rename(filebase+".txt", filebase+".json")
          os.remove(file)          
      except urllib2.URLError, e:
        print "Bulk API file " + file + " failed to download for reason:"
        print e.reason
        print "Aborting execution.."
        sys.exit()


#####################################################################
# Download company-level import .xls files from EIA website
#####################################################################
def pullCompanyLevelImports():
    print 'Retrieving company-level import data from EIA website...'

    inputFile = open('Scenario0001/source/input/Data/STEO/STEO_TimeIdx_Date.csv', 'rt')

    outputFile = open('Scenario0001/source/input/Data/STEO/EIA_CompanyLevelImports.csv','wb')
    writer = csv.writer(outputFile, quoting=csv.QUOTE_ALL)

    reader = csv.DictReader(inputFile)
    time_IDX = list(reader)
    inputFile.close()

    dateDict = dict((i['TimeIdx'],int(i['Date'])) for i in time_IDX)    

    monthly = [str(substractMonths(dateDict['0'],i)) for i in range(1,13)]
    print monthly

    files = []
    baseaddr = 'http://www.eia.gov/petroleum/imports/companylevel/archive/'
    for date in monthly:
      rec = {}
      mm = date[4:6]
      yy = date[0:4]
      rec['Date'] = date
      rec['Address'] = baseaddr + yy + '/' + yy + '_' + mm + '/data/import.xls'
      rec['SaveName'] = 'imports_' + mm + '_' + yy + '.xls'
      files.append(rec)
 
    for count, item in enumerate(files,1):
      mm = item['Date'][4:6]
      yy = item['Date'][0:4]
      print "...Downloading imports.xls for " + mm + '-' + yy 

      try:
        response = urllib2.urlopen(item['Address'])
        content = response.read()
        f = open( item['SaveName'], 'wb' )
        f.write( content )
        f.close()

        wb = xlrd.open_workbook(item['SaveName'])
        try:
          sh = wb.sheet_by_name('IMPORTS')
        except:
          sh = wb.sheet_by_name('Imports')

        if count == 1:
          writer.writerow(sh.row_values(0))
        
        for rownum in range(1,sh.nrows):
          writer.writerow([item['Date']] + sh.row_values(rownum)[1:])

        os.remove(item['SaveName'])

      except urllib2.URLError, e:
        print "File " + item['Address'] + " failed to download for reason:"
        print e.reason
        print "Skipping.."
 
    outputFile.close()         


#####################################################################
# Parse bulk JSON files into ST-LFMM input files
#####################################################################
def parseJSONdata():
    print 'Processing raw API data in Python...'
    
    bulk_API_files=['PET.json',
                    'STEO.json',
                    'SEDS.json']

    mapping_file = 'APIkeys.csv'
    file_specs = 'OutputFileSpecs.csv'

    timeFile = open('Scenario0001/source/input/Data/STEO/STEO_TimeIdx_Date.csv', 'rt')
    reader = csv.DictReader(timeFile)
    time_IDX = list(reader)
    timeFile.close()
    Dates  = sorted(list(set([i['Date'] for i in time_IDX])), key=int)

    hh = open(file_specs, 'r')
    reader = csv.DictReader(hh)
    spec_data = list(reader)
    spec_dict = dict((i['Outfile'].strip(), i) for i in spec_data)
    hh.close()

    mh = open(mapping_file, 'r')
    reader = csv.DictReader(mh)
    # Create a list of dictionaries each containing a line of CSV data
    mapping_data = list(reader)
    mh.close()

    # Get unique set of output files from mapping_file and file_specs
    OutputFiles  = set([i['Outfile'].strip() for i in mapping_data])
    OutputFiles2 = set([i['Outfile'].strip() for i in spec_data])

    # Abort if there are input files in mapping_file that have no match in file_specs
    if (not OutputFiles <= OutputFiles2):
      print "ERROR: The follwing output files in " + mapping_file + " don't have a match in " + file_specs + "!  Aborting.."
      for count,i in enumerate(OutputFiles-OutputFiles2):
        print '....',count+1, i
      sys.exit()

    # Open the output files for writing while creating a dictionary mapping the output filenames to the file handles
    file_dict = dict((i, open(spec_dict[i]['Filepath'].strip()+'/'+i,'w')) for i in OutputFiles)

    # Add the file handles to the CSV data dictionaries
    for m in mapping_data:
      m['filehandle'] = file_dict[m['Outfile']]


    # Write all of the headers to the output CSV files
    for h in OutputFiles:
      file_dict[h].write(spec_dict[h]['Headers']+'\n')

    # Count the number of occurences of the following combination of APIkeys entries, these will be summed up by date
    tuples = [(m['Category'],m['Subcategory'],m['Commodity'],m['Region'],m['Outfile']) for m in mapping_data]
    tuple_count = Counter(tuples)

    # Get the unique set of tuples and initialize a counter dictionary
    tuples = list(set(tuples))
    counter_dict = dict((t,0) for t in tuples)

    # Initialize a data gathering dictionary
    data_dict = dict((t,[]) for t in tuples)

    for file in bulk_API_files:
      with open(file, 'r') as f:
        for line in f:
          data=json.loads(line)
          if 'series_id' in data:
            gen = (x for x in mapping_data if x['series_id'].strip()==data['series_id'].strip())
            for keydata in gen:
              category = keydata['Category']
              subcategory = keydata['Subcategory']
              commodity = keydata['Commodity']
              region = keydata['Region']
              fh = keydata['filehandle'] 
              tup = (keydata['Category'],keydata['Subcategory'],keydata['Commodity'],keydata['Region'],keydata['Outfile'])
              adjFac = float(keydata['AdjFactor'])
              print data['series_id'].strip(), category, commodity, region       

              counter_dict[tup] += 1
              if counter_dict[tup] == tuple_count[tup]:
                data_dict[tup] += data['data']
                for d in sorted(list(set([i[0] for i in data_dict[tup]])), reverse=True):
                  tempval = 0.0
                  matches = [x for x in data_dict[tup] if x[0].strip()==d.strip()]
                  for m in matches: 
                    if m[1] is not None:
                      tempval += m[1] * adjFac

                  if   category.strip()=='Inventory':
                    fh.write('%s,%s,%s,%s,%s\n' % (subcategory, commodity, region, d, tempval))

                  elif category.strip()=='ProductImports':
                    fh.write('%s,%s,%s\n' % (commodity, d, tempval))

                  elif category.strip()=='ProductExports':
                    fh.write('%s,%s,%s\n' % (commodity, d, tempval))

                  elif category.strip()=='CrudeImports':
                    fh.write('%s,%s,%s\n' % (commodity, d, tempval))

                  elif category.strip()=='BrentPrice':
                    fh.write('%s,%s,%s\n' % (commodity, d, tempval))

                  elif category.strip()=='ProductDemands':
                    if commodity.strip().upper() == 'OTHER':
                      # Split "Other liquid fuel demands" into the following products based on 5-year average production quantities
                      fh.write('%s,%s,%s\n' % ('LUBout', d, 0.756*tempval))
                      fh.write('%s,%s,%s\n' % ('AVGout', d, 0.057*tempval))
                      fh.write('%s,%s,%s\n' % ('SPNout', d, 0.187*tempval))
                    else:
                      fh.write('%s,%s,%s\n' % (commodity, d, tempval))

                  elif category.strip()=='ProductDemandsGUI':
                    fh.write('%s,%s,%s\n' % (commodity, d, tempval))    

                  elif category.strip()=='STEOCompare':
                    if d in Dates:    # Strip out historical data
                      fh.write('%s,%s,%s,%s\n' % (subcategory, commodity, d, tempval))                
                          
                  elif category.strip()=='HistoricalPrices':
                    fh.write('%s,%s,%s,%s\n' % (region, commodity, d, tempval))

                  elif category.strip()=='SEDSdata':
                    fh.write('%s,%s,%s,%s\n' % (region, commodity, d, tempval))                    

                  elif category.strip()=='HistCrudeProduction':
                    fh.write('%s,%s,%s\n' % (commodity, d, tempval))                    

                  else:
                    print 'Unknown data category: ', category
              else:
                data_dict[tup] += data['data']   


    # Close the output files
    for o in OutputFiles:
      file_dict[o].close()


#####################################################################
# Process STEO crude production report from EIA
#####################################################################
def processSTEOcrudeRep():

    print "Processing STEO domestic crude production data..."

    # Need to save the STEO crude production spreadsheet tab in CSV format as the following file
    #  before running this code
    inputFile  = open('Scenario0001/source/input/Data/STEO/STEO_DomCrudeReport.csv', 'rt')

    inputFile2 = open('Scenario0001/source/input/Data/STEO/STEO_CrudeTypeSplits.csv', 'rt')
    inputFile3 = open('Scenario0001/source/input/Data/STEO/STEO_CrudeRegSplits.csv', 'rt')
    inputFile4 = open('Scenario0001/source/input/Data/STEO/STEO_TimeIdx_Date.csv', 'rt')
    inputFile5 = open('Scenario0001/source/input/Data/STEO/Map_CrudeReg_to_PADD.csv', 'rt')

    outputFile = open('Scenario0001/source/input/Data/STEO/pySTEO_CrudeProduction.csv','wb')
    writer = csv.writer(outputFile)
    writer.writerow(['TimeIdx','Site_Name','CrudeType','Quantity']) 

    reader = csv.DictReader(inputFile)
    production_data = list(reader)
    inputFile.close()

    reader = csv.DictReader(inputFile2)
    type_splits = list(reader)
    inputFile2.close()

    reader = csv.DictReader(inputFile3)
    reg_splits = list(reader)
    inputFile3.close()

    reader = csv.DictReader(inputFile4)
    time_IDX = list(reader)
    inputFile4.close()

    reader = csv.DictReader(inputFile5)
    CrudeReg_2_PADD = list(reader)
    inputFile5.close()

    dateDict = dict((i['Date'],i['TimeIdx']) for i in time_IDX)

    def fixDate(year_month):
      return year_month.split('M')[0].strip()+year_month.split('M')[1].strip()

    # Rearrage the STEO crude production data dictionary from table format to a "database" format
    r = []
    d = {}
    newrecs = (x for x in production_data if fixDate(x['Date']) in [d['Date'] for d in time_IDX])
    for record in newrecs:
      date = fixDate(record['Date'])
      timeIndex = dateDict[date]
      gen = (x for x in record if x != 'Date')
      for key in gen:
        d = {}
        d['Date'] = date
        d['TimeIdx'] = timeIndex
        d['CrudeBasin'] = key
        d['Volume'] = record[key]
        r.append(d)


    CrudeReg   = sorted(list(set([i['CrudeReg'] for i in reg_splits])))
    PADD       = sorted(list(set([i['PADD'] for i in CrudeReg_2_PADD])))
    CrudeType  = sorted(list(set([i['CrudeType'] for i in type_splits])))
    CrudeBasin = sorted(list(set([i['CrudeBasin'] for i in type_splits])))
    TimeIdx    = sorted(list(set([i['TimeIdx'] for i in time_IDX])), key=float)

    # Dictionaries to hold total crude production by crude region and PADD regions in last historical time period
    total_by_CrudeReg = dict((i,0) for i in itertools.product(CrudeReg,CrudeType))
    total_by_PADD = dict((i,0) for i in PADD)

    # Dictionary for valid (CrudeReg,PADD) mapping data pairs and their fractions
    CrudeReg_PADD_frac = dict(((i['CrudeReg'],i['PADD']),float(i['Fraction'])) for i in CrudeReg_2_PADD if i['PADD'].strip() != 'US')

    # Dictionary to hold the calculation of the fraction of PADD production that comes from each CrudeReg in last historical time period
    PADD_CrudeReg_frac = dict(((i['PADD'],i['CrudeReg']),0) for i in CrudeReg_2_PADD if i['PADD'].strip() != 'US')

    # Dictionary to hold the calculation of the fractions of production by CrudeType for each CrudeReg in last historical time period
    CrudeReg_CrudeType_frac = dict(((i[0],i[1]),0) for i in itertools.product(CrudeReg,CrudeType))

    # Iterate over all (TimeIdx,CrudeReg,CrudeType) pairs and CrudeBasins to calculate domestic crude production by CrudeReg and CrudeType
    for i in itertools.product(TimeIdx,CrudeReg,CrudeType):
      volume = 0
      for b in CrudeBasin:
        typefrac = next((float(item['Fraction']) for item in type_splits if item['CrudeBasin']==b and item['CrudeType']==i[2]), 0) 
        regfrac  = next((float(item['Fraction']) for item in reg_splits if item['CrudeBasin']==b and item['CrudeReg']==i[1]), 0)
        tempvol  = next((float(item['Volume']) for item in r if item['CrudeBasin']==b and item['TimeIdx']==i[0]), 0)
        volume  += typefrac * regfrac * tempvol

      writer.writerow([i[0],i[1],i[2],volume]) 

      if i[0]=='-1':
        total_by_CrudeReg[(i[1],i[2])] = volume
        for p in [x for x in PADD if (i[1],x) in CrudeReg_PADD_frac.keys()]:
          total_by_PADD[p] += volume * CrudeReg_PADD_frac[(i[1],p)]

    outputFile.close()

    for k in PADD_CrudeReg_frac.keys():
      if total_by_PADD[k[0]] > 0:
        PADD_CrudeReg_frac[k] = sum(total_by_CrudeReg[(k[1],x)] for x in CrudeType) * CrudeReg_PADD_frac[(k[1],k[0])] / total_by_PADD[k[0]]
      else:
        PADD_CrudeReg_frac[k] = 0

    for k in CrudeReg_CrudeType_frac.keys():
      tempsum = sum(total_by_CrudeReg[(k[0],x)] for x in CrudeType)
      if tempsum > 0:
        CrudeReg_CrudeType_frac[k] = total_by_CrudeReg[k] / tempsum
      else:
        CrudeReg_CrudeType_frac[k] = 0        

    return PADD_CrudeReg_frac, CrudeReg_CrudeType_frac

    
#####################################################################
# Process STEO storage capacities
#####################################################################
def processInventories(PADD_CrudeReg_frac,CrudeReg_CrudeType_frac,RefReg_Summer_Frac):

    print "Processing PSM inventory data..."

    # Need to save the STEO crude production spreadsheet tab in CSV format as the following file
    #  before running this code
    inputFile  = open('Scenario0001/source/input/Data/STEO/aPSM_Inventories.csv', 'rt')
    inputFile2 = open('Scenario0001/source/input/Data/STEO/Map_PADD_to_RefReg_ACU.csv', 'rt')
    inputFile3 = open('Scenario0001/source/input/Data/STEO/Map_CrudeReg_to_RefReg.csv', 'rt')
    inputFile4 = open('Scenario0001/source/input/Data/STEO/STEO_TimeIdx_Date.csv', 'rt')

    outputFile = open('Scenario0001/source/input/Data/STEO/pyPSM_InventoryBounds.csv','wb')
    writer = csv.writer(outputFile)
    writer.writerow(['Category','Commodity','Region','Month','LowerBound']) 

    outputFile2 = open('Scenario0001/source/input/Data/STEO/pyPSM_StartingInventory.csv','wb')
    writer2 = csv.writer(outputFile2)
    writer2.writerow(['Category','Commodity','Region','Start'])     

    reader = csv.DictReader(inputFile)
    stock_data = list(reader)
    inputFile.close()

    reader = csv.DictReader(inputFile2)
    PADD_2_RefReg = list(reader)
    inputFile2.close()

    reader = csv.DictReader(inputFile3)
    CrudeReg_2_RefReg = list(reader)
    inputFile3.close()    

    reader = csv.DictReader(inputFile4)
    time_IDX = list(reader)
    inputFile4.close()

    timeDict   = dict((i['TimeIdx'],int(i['Date'])) for i in time_IDX)    

    RefReg       = sorted(list(set([i['RefReg'] for i in PADD_2_RefReg])))
    PADD         = sorted(list(set([i['PADD'] for i in PADD_2_RefReg])))
    CrudeReg     = sorted(list(set([i[1] for i in PADD_CrudeReg_frac.keys()])))
    CrudeType    = sorted(list(set([i[1] for i in CrudeReg_CrudeType_frac.keys()])))

    # Fraction of PADD ACU capacity in each RefReg
    PADD_RefReg_ACU = dict(((i['PADD'],i['RefReg']),float(i['Fraction'])) for i in PADD_2_RefReg)

    # Fraction of PADD ACU capacity in each RefReg
    CrudeReg_RefReg = dict(((i['CrudeReg'],i['RefReg']),float(i['Fraction'])) for i in CrudeReg_2_RefReg)    
    
    MonthlyData   = [i for i in stock_data if i['Category'] != 'Weekly']
    AllWeeklyData = [i for i in stock_data if i['Category'] == 'Weekly']

    # Get list of unique monthly dates (yyyymm) from non-weekly data
    mDates = sorted(list(set([i['Date'] for i in MonthlyData if int(i['Date']) in range(substractMonths(timeDict['0'],48),timeDict['0'])])), key=int)

    # Get list of unique weekly dates (yyyymmdd) from weekly data that are after the final monthly date
    wDates = sorted(list(set([i['Date'] for i in AllWeeklyData if i['Date'][0:6] not in mDates and timeDict['0']>int(i['Date'][0:6])>int(mDates[0])])), key=int)

    Dates  = sorted(list(set(mDates+[i['Date'][0:6] for i in AllWeeklyData if i['Date'][0:6] not in mDates and timeDict['0']>int(i['Date'][0:6])>int(mDates[0])])), key=int)

    # Get list of latest monthly date for each month in the weekly data
    wDatesLast = sorted(list(set([i for i in wDates if i in max([j for j in wDates if j[0:6]==i[0:6]])])), key=int)

    WeeklyData  = [i for i in stock_data if i['Category'] == 'Weekly' and i['Date'] in wDatesLast]

    InvCategory  = sorted(list(set([i['Category'] for i in MonthlyData])))

    UFOs      = ['GO3','GO7','KR3','KR7','MN3','VR3','VR7']
    Other     = ['AVGout','COKout','GO3out','GO7out','LUBout','NAPout','PCFout','SPNout']
    NGL       = ['IC4','NAT','NC4','PGS']

    SummerGas = ['CaRBOBs','CaRBOBsout','CBOBs','CFGsout','RBOBs','RFGsout']
    WinterGas = ['CaRBOBw','CaRBOBwout','CBOBw','CFGwout','RBOBw','RFGwout']
    Map_Summer_Winter = dict(zip(SummerGas, WinterGas))  

    # Get summer-winter gasoline fractions by month instead of date
    RefReg_Summer_Frac_month = {}
    for i in RefReg_Summer_Frac:
      mm = int(i[1][4:6])
      tup = (i[0],mm)
      if tup not in RefReg_Summer_Frac_month.keys():
        RefReg_Summer_Frac_month[tup] = RefReg_Summer_Frac[i]


    # Iterate over all MONTHLY inventory data records and split out into crude types, products, and ST-LFMM refining regions 
    newinv = []
    for record in [i for i in MonthlyData if i['Date'] in mDates]:
      if record['Commodity'] != 'crudeoil':
        for r in [x for x in RefReg if (record['Region'],x) in PADD_RefReg_ACU.keys()]:
          vol = float(record['Volume'])*PADD_RefReg_ACU[(record['Region'],r)]

          d = {}
          d['Category']  = record['Category']
          d['Commodity'] = record['Commodity']
          d['Region']    = r
          d['Date']      = record['Date']
          d['Volume']    = vol
          newinv.append(d)          

      else:
      
        if record['Category']=='Refineries':
          # Get volume by crude type in this PADD and split into refining regions
          for t in CrudeType:
            vol = 0
            for c in [x for x in CrudeReg if (record['Region'],x) in PADD_CrudeReg_frac.keys() and (x,t) in CrudeReg_CrudeType_frac.keys()]:            
              vol += float(record['Volume']) * PADD_CrudeReg_frac[(record['Region'],c)] * CrudeReg_CrudeType_frac[(c,t)]

            for r in [z for z in RefReg if (record['Region'],z) in PADD_RefReg_ACU.keys()]:              
              
              d = {}
              d['Category']  = record['Category']
              d['Commodity'] = t
              d['Region']    = r
              d['Date']      = record['Date']
              d['Volume']    = vol * PADD_RefReg_ACU[(record['Region'],r)] 
              newinv.append(d)     

        if record['Category']=='BulkTerminal':
          # Get volume by crude type in this PADD and split into refining regions
          for t in CrudeType:
            vol = 0
            for c in [x for x in CrudeReg if (record['Region'],x) in PADD_CrudeReg_frac.keys() and (x,t) in CrudeReg_CrudeType_frac.keys()]:            
              vol += float(record['Volume']) * PADD_CrudeReg_frac[(record['Region'],c)] * CrudeReg_CrudeType_frac[(c,t)]

            for r in [z for z in RefReg if (record['Region'],z) in PADD_RefReg_ACU.keys()]:              
              
              d = {}
              d['Category']  = record['Category']
              d['Commodity'] = t
              d['Region']    = r
              d['Date']      = record['Date']
              d['Volume']    = vol / len([zz for zz in RefReg if (record['Region'],zz) in PADD_RefReg_ACU.keys()])
              newinv.append(d)    

        elif record['Category']=='AKinTransit':
          for c in [x for x in CrudeReg if (record['Region'],x) in PADD_CrudeReg_frac.keys()]:
            vol = float(record['Volume']) * PADD_CrudeReg_frac[(record['Region'],c)]           
            d = {}
            d['Category']  = record['Category']
            d['Commodity'] = 'M_Msour'
            d['Region']    = c
            d['Date']      = record['Date']
            d['Volume']    = vol
            newinv.append(d)              

        else:
          for c in [x for x in CrudeReg if (record['Region'],x) in PADD_CrudeReg_frac.keys()]:
            for t in [y for y in CrudeType if (c,y) in CrudeReg_CrudeType_frac.keys()]:
              vol = float(record['Volume']) * PADD_CrudeReg_frac[(record['Region'],c)] * CrudeReg_CrudeType_frac[(c,t)]          
              d = {}
              d['Category']  = record['Category']
              d['Commodity'] = t
              d['Region']    = c
              d['Date']      = record['Date']
              d['Volume']    = vol
              newinv.append(d)               


    # Iterate over all WEEKLY inventory data records and split out into crude types, products, and ST-LFMM regions 
    weeklyinv = []
    for record in [i for i in WeeklyData if i['Date'] in wDatesLast]:
      if record['Commodity'] == 'crudeoil':
        # At PADD level, needs to be broken out by crude type and CrudeReg/RefReg
        oldvol = sum(i['Volume'] for i in newinv if i['Commodity'] in CrudeType and i['Date']==mDates[-1] and ((record['Region'],i['Region']) in PADD_RefReg_ACU.keys() or (record['Region'],i['Region']) in PADD_CrudeReg_frac.keys()))
        
        if oldvol > 0:
          adjfactor = float(record['Volume']) / oldvol 
        else:
          adjfactor = 1

        for j in [i for i in newinv if i['Commodity'] in CrudeType and i['Date']==mDates[-1] and ((record['Region'],i['Region']) in PADD_RefReg_ACU.keys() or (record['Region'],i['Region']) in PADD_CrudeReg_frac.keys())]:
          d = {}
          d['Category']  = j['Category']
          d['Commodity'] = j['Commodity']
          d['Region']    = j['Region']
          d['Date']      = record['Date'][0:6]
          d['Volume']    = j['Volume'] * adjfactor
          weeklyinv.append(d)          

      elif record['Commodity'] == 'ASPHout':
        # At US level
        oldvol = sum(i['Volume'] for i in newinv if i['Commodity']=='ASPHout' and i['Date']==mDates[-1])
        
        if oldvol > 0:
          adjfactor = float(record['Volume']) / oldvol 
        else:
          adjfactor = 1

        for j in [i for i in newinv if i['Commodity']=='ASPHout' and i['Date']==mDates[-1]]:
          d = {}
          d['Category']  = j['Category']
          d['Commodity'] = j['Commodity']
          d['Region']    = j['Region']
          d['Date']      = record['Date'][0:6]
          d['Volume']    = j['Volume'] * adjfactor
          weeklyinv.append(d)  

      elif record['Commodity'] == 'LPGout':
        # PADDs 4+5 are combined so we need to split them out 

        if record['Region'] == 'PADD45':
          lastMonth_P4 = sum(i['Volume'] for i in newinv if i['Commodity']==record['Commodity'] and ('PADD4',i['Region']) in PADD_RefReg_ACU.keys() and i['Date']==mDates[-1])
          lastMonth_P5 = sum(i['Volume'] for i in newinv if i['Commodity']==record['Commodity'] and ('PADD5',i['Region']) in PADD_RefReg_ACU.keys() and i['Date']==mDates[-1])

          oldvol = sum(i['Volume'] for i in newinv if i['Commodity']==record['Commodity'] and i['Date']==mDates[-1] and ('PADD4',i['Region']) in PADD_RefReg_ACU.keys())          
        
          if oldvol > 0:
            adjfactor = (lastMonth_P4/(lastMonth_P4+lastMonth_P5)) * float(record['Volume']) / oldvol 
          else:
            adjfactor = 1

          for j in [i for i in newinv if i['Commodity']==record['Commodity'] and i['Date']==mDates[-1] and ('PADD4',i['Region']) in PADD_RefReg_ACU.keys()]:
            d = {}
            d['Category']  = j['Category']
            d['Commodity'] = j['Commodity']
            d['Region']    = j['Region']
            d['Date']      = record['Date'][0:6]
            d['Volume']    = j['Volume'] * adjfactor
            weeklyinv.append(d)               

          # PADD 5
          oldvol = sum(i['Volume'] for i in newinv if i['Commodity']==record['Commodity'] and i['Date']==mDates[-1] and ('PADD5',i['Region']) in PADD_RefReg_ACU.keys())
          
          if oldvol > 0:
            adjfactor = (lastMonth_P5/(lastMonth_P4+lastMonth_P5)) * float(record['Volume']) / oldvol 
          else:
            adjfactor = 1

          for j in [i for i in newinv if i['Commodity']==record['Commodity'] and i['Date']==mDates[-1] and ('PADD5',i['Region']) in PADD_RefReg_ACU.keys()]:
            d = {}
            d['Category']  = j['Category']
            d['Commodity'] = j['Commodity']
            d['Region']    = j['Region']
            d['Date']      = record['Date'][0:6]
            d['Volume']    = j['Volume'] * adjfactor
            weeklyinv.append(d)                

        else:
          oldvol = sum(i['Volume'] for i in newinv if i['Commodity']==record['Commodity'] and i['Date']==mDates[-1] and (record['Region'],i['Region']) in PADD_RefReg_ACU.keys())

          if oldvol > 0:
            adjfactor = float(record['Volume']) / oldvol 
          else:
            adjfactor = 1
          
          for j in [i for i in newinv if i['Commodity']==record['Commodity'] and i['Date']==mDates[-1] and (record['Region'],i['Region']) in PADD_RefReg_ACU.keys()]:
            d = {}
            d['Category']  = j['Category']
            d['Commodity'] = j['Commodity']
            d['Region']    = j['Region']
            d['Date']      = record['Date'][0:6]
            d['Volume']    = j['Volume'] * adjfactor
            weeklyinv.append(d) 

      elif record['Commodity'] == 'Other':
        # Many products combined at national level
        # oldvol = sum(i['Volume'] for i in newinv if i['Commodity'] in Other and i['Date']==mDates[-1])

        # Use jet fuel as a proxy since I cannot figure out the weekly "Other" accounting
        oldvol = sum(i['Volume'] for i in newinv if i['Commodity']=='JTAout' and i['Date']==mDates[-1])
        newvol = sum(float(i['Volume']) for i in WeeklyData if i['Commodity']=='JTAout' and i['Date']==record['Date'])

        if oldvol > 0:
          adjfactor = newvol / oldvol 
        else:
          adjfactor = 1
        
        for j in [i for i in newinv if i['Commodity'] in Other and i['Date']==mDates[-1]]:
          d = {}
          d['Category']  = j['Category']
          d['Commodity'] = j['Commodity']
          d['Region']    = j['Region']
          d['Date']      = record['Date'][0:6]
          d['Volume']    = j['Volume'] * adjfactor
          weeklyinv.append(d)  

      elif record['Commodity'] == 'UFO':
        # Many products combined at national level
        oldvol = sum(i['Volume'] for i in newinv if i['Commodity'] in UFOs and i['Date']==mDates[-1])

        if oldvol > 0:
          adjfactor = float(record['Volume']) / oldvol 
        else:
          adjfactor = 1
        
        for j in [i for i in newinv if i['Commodity'] in UFOs and i['Date']==mDates[-1]]:
          d = {}
          d['Category']  = j['Category']
          d['Commodity'] = j['Commodity']
          d['Region']    = j['Region']
          d['Date']      = record['Date'][0:6]
          d['Volume']    = j['Volume'] * adjfactor
          weeklyinv.append(d)  

      elif record['Commodity'] == 'NGL':
        # Many products combined at national level
        oldvol = sum(i['Volume'] for i in newinv if i['Commodity'] in NGL and i['Date']==mDates[-1])

        if oldvol > 0:
          adjfactor = float(record['Volume']) / oldvol 
        else:
          adjfactor = 1
        
        for j in [i for i in newinv if i['Commodity'] in NGL and i['Date']==mDates[-1]]:
          d = {}
          d['Category']  = j['Category']
          d['Commodity'] = j['Commodity']
          d['Region']    = j['Region']
          d['Date']      = record['Date'][0:6]
          d['Volume']    = j['Volume'] * adjfactor
          weeklyinv.append(d) 

      else:
        oldvol = sum(i['Volume'] for i in newinv if i['Commodity']==record['Commodity'] and i['Date']==mDates[-1] and (record['Region'],i['Region']) in PADD_RefReg_ACU.keys())

        if oldvol > 0:
          adjfactor = float(record['Volume']) / oldvol 
        else:
          adjfactor = 1
                
        for j in [i for i in newinv if i['Commodity']==record['Commodity'] and i['Date']==mDates[-1] and (record['Region'],i['Region']) in PADD_RefReg_ACU.keys()]:   

          d = {}
          d['Category']  = j['Category']
          d['Commodity'] = j['Commodity']
          d['Region']    = j['Region']
          d['Date']      = record['Date'][0:6]
          d['Volume']    = j['Volume'] * adjfactor
          weeklyinv.append(d)           
    
    # Combine monthly and weekly data
    newinv += weeklyinv

    # Change CARB product inventories to regular products in non-California PADD 5
    for r in newinv:
      if r['Region']=='8_RefReg' and (r['Commodity']=='CaRBOBs' or r['Commodity']=='CaRBOBsout' or r['Commodity']=='CarbDSUout'):
        r.update((k, 'RBOBs') for k, v in r.iteritems() if k=='Commodity' and v=='CaRBOBs')
        r.update((k, 'RFGsout') for k, v in r.iteritems() if k=='Commodity' and v=='CaRBOBsout')
        r.update((k, 'DSUout') for k, v in r.iteritems() if k=='Commodity' and v=='CarbDSUout')


    # Create inventory lower bounds as historical average by month
    for rec in set([(x['Category'],x['Commodity'],x['Region']) for x in newinv]):

      for month in range(1,13):
        mylist  = [i['Volume'] for i in newinv if i['Category']==rec[0] and i['Commodity']==rec[1] and i['Region']==rec[2] and i['Date'] in Dates and int(i['Date'][4:6])==month]
        if len(mylist)>0:
          LowerBound  = float(sum(mylist)) / len(mylist)
        else:
          LowerBound = 0

        if rec[1] in SummerGas:
          # Separate gasoline lower bounds according to summer/winter splits by region/month
          summerfrac = RefReg_Summer_Frac_month[(rec[2],month)]
          winterfrac = 1 - RefReg_Summer_Frac_month[(rec[2],month)]

          writer.writerow([rec[0],rec[1],rec[2],month,summerfrac*LowerBound])
          writer.writerow([rec[0],Map_Summer_Winter[rec[1]],rec[2],month,winterfrac*LowerBound])
        else:
          writer.writerow([rec[0],rec[1],rec[2],month,LowerBound])
      
      # Starting inventories
      last = next((i['Volume'] for i in newinv if i['Category']==rec[0] and i['Commodity']==rec[1] and i['Region']==rec[2] and int(i['Date'])==timeDict['-1']),0.0)
      if rec[1] in SummerGas:
        # Separate starting gasoline inventories according to summer/winter splits by region
        summerfrac = RefReg_Summer_Frac[(rec[2],str(timeDict['0']))]
        winterfrac = 1 - RefReg_Summer_Frac[(rec[2],str(timeDict['0']))]

        writer2.writerow([rec[0],rec[1],rec[2],summerfrac*last])
        writer2.writerow([rec[0],Map_Summer_Winter[rec[1]],rec[2],winterfrac*last])
      else:
        writer2.writerow([rec[0],rec[1],rec[2],last])
 
    outputFile.close()
    outputFile2.close()



#####################################################################
# Process STEO storage capacities
#####################################################################
def processStorageCap(PADD_CrudeReg_frac):

    print "Processing STEO storage capacity data..."

    # Need to save the STEO crude production spreadsheet tab in CSV format as the following file
    #  before running this code
    inputFile  = open('Scenario0001/source/input/Data/STEO/EIA_StorageCapacity.csv', 'rt')
    inputFile2 = open('Scenario0001/source/input/Data/STEO/Map_PADD_to_RefReg_ACU.csv', 'rt')

    outputFile = open('Scenario0001/source/input/Data/STEO/pyPSM_StorageCapacity.csv','wb')
    writer = csv.writer(outputFile)
    writer.writerow(['Category','Commodity','Region','Volume']) 

    reader = csv.DictReader(inputFile)
    storage_data = list(reader)
    inputFile.close()

    reader = csv.DictReader(inputFile2)
    PADD_2_RefReg = list(reader)
    inputFile2.close()

    RefReg    = sorted(list(set([i['RefReg'] for i in PADD_2_RefReg])))
    PADD      = sorted(list(set([i['PADD'] for i in PADD_2_RefReg])))
    CrudeReg  = sorted(list(set([i[1] for i in PADD_CrudeReg_frac.keys()])))

    # Fraction of PADD ACU capacity in each RefReg
    PADD_RefReg_ACU = dict(((i['PADD'],i['RefReg']),float(i['Fraction'])) for i in PADD_2_RefReg)


    # Iterate over all storage data records
    for record in storage_data:
      
      if record['Category']=='Refineries' or record['Category']=='BulkTerminal' or (record['Category']=='Pipelines' and record['Commodity']!='crudeoil'):
        for r in [x for x in RefReg if (record['Region'],x) in PADD_RefReg_ACU.keys()]:
          writer.writerow([record['Category'],record['Commodity'],r,float(record['Value'])*PADD_RefReg_ACU[(record['Region'],r)]])
      else:
        for c in [x for x in CrudeReg if (record['Region'],x) in PADD_CrudeReg_frac.keys()]:
          writer.writerow([record['Category'],record['Commodity'],c,float(record['Value'])*PADD_CrudeReg_frac[(record['Region'],c)]])
      

    outputFile.close()


#####################################################################
# Process STEO product demands
#####################################################################
def processDemands():

    print "Processing STEO demand data..."

    inputFile  = open('Scenario0001/source/input/Data/STEO/aSTEO_ProductDemands.csv', 'rt')
    inputFile2 = open('Scenario0001/source/input/Data/STEO/SEDS_DemandSplits.csv', 'rt')
    inputFile3 = open('Scenario0001/source/input/Data/STEO/STEO_TimeIdx_Date.csv', 'rt')
    inputFile4 = open('Scenario0001/source/input/Data/STEO/RFG_Fractions.csv', 'rt')
    inputFile5 = open('Scenario0001/source/input/Data/STEO/Summer_Gasoline_Frac.csv', 'rt')
    inputFile6 = open('Scenario0001/source/input/Data/STEO/Map_State_to_RefReg_ACU.csv', 'rt')

    outputFile = open('Scenario0001/source/input/Data/STEO/pySTEO_ProductDemands.csv','wb')
    writer = csv.writer(outputFile)
    writer.writerow(['Commodity','Region','TimeIdx','Volume']) 

    reader = csv.DictReader(inputFile)
    demand_data = list(reader)
    inputFile.close()

    reader = csv.DictReader(inputFile2)
    demand_splits = list(reader)
    inputFile2.close()   

    reader = csv.DictReader(inputFile3)
    time_IDX = list(reader)
    inputFile3.close()

    reader = csv.DictReader(inputFile4)
    RFG_Fractions = list(reader)
    inputFile4.close()

    reader = csv.DictReader(inputFile5)
    Summer_Fraction = list(reader)
    inputFile5.close()

    reader = csv.DictReader(inputFile6)
    State_RefReg = list(reader)
    inputFile6.close()    

    dateDict = dict((i['Date'],i['TimeIdx']) for i in time_IDX)  

    fracDict = dict(((i['Commodity'],i['Region']),float(i['Fraction'])) for i in demand_splits)  

    Regions = sorted(list(set([i['Region'] for i in demand_splits])))
    Dates   = sorted(list(set([i['Date'] for i in time_IDX])), key=int)
    RefReg  = sorted(list(set([i['Region'] for i in State_RefReg])))

    SummerFracDict  = dict(((i['Region'],i['Month'].zfill(2)),float(i['Fraction'])) for i in Summer_Fraction)
    RFGFracDict     = dict((i['Region'],float(i['Fraction'])) for i in RFG_Fractions) 
    State_2_RefReg  = dict(((i['state'],i['Region']),float(i['Fraction'])) for i in State_RefReg)

    RefReg_Dates       = list(itertools.product(RefReg,Dates))
    RefReg_totals      = dict((i,{'Summer':0,'Total':0}) for i in RefReg_Dates)
    RefReg_Summer_Frac = dict((i,0) for i in RefReg_Dates)   

    for data in [x for x in demand_data if x['Date'] in Dates]:
      for reg in Regions:

        if data['Commodity'].strip()=='CFGsout':
          # Split up gasoline into summer/winter and CARB/CFG/RFG in addition to by state
          sfrac   = SummerFracDict[(reg,data['Date'][4:6])]
          rfgfrac = RFGFracDict[reg]

          # Keep a running total of summer and winter gasoline by RefReg to calculate RefReg-level fractions for use with inventory and imports/exports
          for r in [y for y in RefReg if (reg,y) in State_2_RefReg.keys()]:
            RefReg_totals[(r,data['Date'])]['Summer'] += State_2_RefReg[(reg,r)] * sfrac*float(data['Volume'])*fracDict[(data['Commodity'],reg)]
            RefReg_totals[(r,data['Date'])]['Total']  += State_2_RefReg[(reg,r)] * float(data['Volume'])*fracDict[(data['Commodity'],reg)]

          if reg.strip() == 'CA':
            writer.writerow(['CaRBOBsout',reg,dateDict[data['Date']],sfrac*float(data['Volume'])*fracDict[(data['Commodity'],reg)]])
            writer.writerow(['CaRBOBwout',reg,dateDict[data['Date']],(1-sfrac)*float(data['Volume'])*fracDict[(data['Commodity'],reg)]])

          else:
            writer.writerow(['CFGsout',reg,dateDict[data['Date']],(1-rfgfrac)*sfrac*float(data['Volume'])*fracDict[(data['Commodity'],reg)]])
            writer.writerow(['CFGwout',reg,dateDict[data['Date']],(1-rfgfrac)*(1-sfrac)*float(data['Volume'])*fracDict[(data['Commodity'],reg)]])            
            writer.writerow(['RFGsout',reg,dateDict[data['Date']],rfgfrac*sfrac*float(data['Volume'])*fracDict[(data['Commodity'],reg)]])
            writer.writerow(['RFGwout',reg,dateDict[data['Date']],rfgfrac*(1-sfrac)*float(data['Volume'])*fracDict[(data['Commodity'],reg)]])   

        else:
          # Split up by state
          writer.writerow([data['Commodity'],reg,dateDict[data['Date']],float(data['Volume'])*fracDict[(data['Commodity'],reg)]])
   

    # Calculate summer/winter gasoline split by RefReg for each time period
    for d in Dates:
      summerUS = 0
      totalUS  = 0
      for r in RefReg:       
        RefReg_Summer_Frac[(r,d)] = RefReg_totals[(r,d)]['Summer']/RefReg_totals[(r,d)]['Total']
        summerUS += RefReg_totals[(r,d)]['Summer']
        totalUS += RefReg_totals[(r,d)]['Total']
      RefReg_Summer_Frac[('US',d)] = summerUS/totalUS    

    outputFile.close()

    return RefReg_Summer_Frac


#####################################################################
# Process STEO storage capacities
#####################################################################
def processImportsExports(RefReg_Summer_Frac):

    print "Processing PSM product import and export data..."

    # Need to save the STEO crude production spreadsheet tab in CSV format as the following file
    #  before running this code
    inputFile  = open('Scenario0001/source/input/Data/STEO/aPSM_ProductImports.csv', 'rt')
    inputFile2 = open('Scenario0001/source/input/Data/STEO/aPSM_ProductExports.csv', 'rt')
    inputFile3 = open('Scenario0001/source/input/Data/STEO/aPSM_CrudeImports.csv', 'rt')
    inputFile4 = open('Scenario0001/source/input/Data/STEO/PSM_CrudeImportElast.csv', 'rt')
    inputFile5 = open('Scenario0001/source/input/Data/STEO/PSM_CrudeImportFrac.csv', 'rt')
    inputFile6 = open('Scenario0001/source/input/Data/STEO/STEO_TimeIdx_Date.csv', 'rt')

    outputFile = open('Scenario0001/source/input/Data/STEO/pyPSM_ImportsExports.csv','wb')
    writer = csv.writer(outputFile)
    writer.writerow(['Category','TimeIdx','Commodity','Volume']) 

    outputFile2 = open('Scenario0001/source/input/Data/STEO/pyPSM_CrudeImports.csv','wb')
    writer2 = csv.writer(outputFile2)
    writer2.writerow(['Commodity','Step','Volume'])     

    reader = csv.DictReader(inputFile)
    import_data = list(reader)
    inputFile.close()

    reader = csv.DictReader(inputFile2)
    export_data = list(reader)
    inputFile2.close()

    reader = csv.DictReader(inputFile3)
    crude_data = list(reader)
    inputFile3.close()  

    reader = csv.DictReader(inputFile4)
    elasticity_data = list(reader)
    inputFile4.close()

    reader = csv.DictReader(inputFile5)
    crude_frac = list(reader)
    inputFile5.close()    

    reader = csv.DictReader(inputFile6)
    time_IDX = list(reader)
    inputFile6.close()

    timeDict   = dict((i['TimeIdx'],int(i['Date'])) for i in time_IDX)  
    dateDict   = dict((i['Date'],i['TimeIdx']) for i in time_IDX)  
    ModelDates = sorted(list(set([i['Date'] for i in time_IDX])), key=int)
    Dates      = sorted(list(set([i['Date'] for i in import_data if int(i['Date']) in range(substractMonths(timeDict['0'],24),timeDict['0'])])), key=int)
    CrudeDates = sorted(list(set([i['Date'] for i in crude_data if int(i['Date']) in range(substractMonths(timeDict['0'],60),timeDict['0'])])), key=int)

    CrudeType = sorted(list(set([i['CrudeType'] for i in crude_frac])))
    Steps     = sorted(list(set([i['Step'] for i in elasticity_data])))

    CrudeTypeFrac = dict((i['CrudeType'],i['Fraction']) for i in crude_frac)
    StepFrac      = dict((i['Step'],i['Fraction']) for i in elasticity_data)

    SummerGas = ['CaRBOBs','CaRBOBsout','CBOBs','CFGsout','RBOBs','RFGsout']
    WinterGas = ['CaRBOBw','CaRBOBwout','CBOBw','CFGwout','RBOBw','RFGwout']
    Map_Summer_Winter = dict(zip(SummerGas, WinterGas))     

    # Calculate center points for the product import and export curves

    # Product Imports
    for rec in set([x['Commodity'] for x in import_data]):
      # avg = float(sum(float(i['Volume']) for i in import_data if i['Commodity']==rec and i['Date'] in Dates)) / len(Dates)
      # maxval = float(max(float(i['Volume']) for i in import_data if i['Commodity']==rec and i['Date'] in Dates))
      mylist  = [float(i['Volume']) for i in import_data if i['Commodity']==rec and i['Date'] in Dates]
      if len(mylist)>0:
        percent = percentile(mylist, 80)
      else:
        percent = 0

      for d in ModelDates:
        if rec in SummerGas:
          # Separate starting gasoline inventories and lower bounds according to summer/winter splits by region
          if rec == 'CaRBOBs':
            summerfrac = RefReg_Summer_Frac[('7_RefReg',d)]
            winterfrac = 1 - RefReg_Summer_Frac[('7_RefReg',d)]
          else:
            summerfrac = RefReg_Summer_Frac[('US',d)]
            winterfrac = 1 - RefReg_Summer_Frac[('US',d)]

          writer.writerow(['ProductImports',dateDict[d],rec,summerfrac*percent])
          writer.writerow(['ProductImports',dateDict[d],Map_Summer_Winter[rec],winterfrac*percent])
        else:
          writer.writerow(['ProductImports',dateDict[d],rec,percent])      

    # Product Exports
    for rec in set([x['Commodity'] for x in export_data]):
      # avg = float(sum(float(i['Volume']) for i in export_data if i['Commodity']==rec and i['Date'] in Dates)) / len(Dates)
      # maxval = float(max(float(i['Volume']) for i in export_data if i['Commodity']==rec and i['Date'] in Dates))
      mylist  = [float(i['Volume']) for i in export_data if i['Commodity']==rec and i['Date'] in Dates]
      if len(mylist)>0:
        percent = percentile(mylist, 80)
      else:
        percent = 0

      for d in ModelDates:
        if rec in SummerGas:
          # Separate starting gasoline inventories and lower bounds according to summer/winter splits by region
          summerfrac = RefReg_Summer_Frac[('US',d)]
          winterfrac = 1 - RefReg_Summer_Frac[('US',d)]

          writer.writerow(['ProductExports',dateDict[d],rec,summerfrac*percent])
          writer.writerow(['ProductExports',dateDict[d],Map_Summer_Winter[rec],winterfrac*percent])
        else:
          writer.writerow(['ProductExports',dateDict[d],rec,percent])   


    # Crude oil imports
    # avg = float(sum(float(i['Volume']) for i in crude_data if i['Date'] in Dates)) / len(Dates)
    # maxval = float(max(float(i['Volume']) for i in crude_data if i['Date'] in Dates))
    mylist  = [float(i['Volume']) for i in crude_data if i['Date'] in CrudeDates]
    if len(mylist)>0:
      percent = percentile(mylist, 80)
    else:
      percent = 0

    for i in CrudeType:
      for j in Steps:
        writer2.writerow([i,j,percent*float(CrudeTypeFrac[i])*float(StepFrac[j])])

    outputFile.close()
    outputFile2.close()


#####################################################################
# Process STEO storage capacities
#####################################################################
def processCrudePrices():

    print "Processing Brent price data..."

    inputFile  = open('Scenario0001/source/input/Data/STEO/aSTEO_BrentPrice.csv', 'rt')
    inputFile2 = open('Scenario0001/source/input/Data/STEO/STEO_TimeIdx_Date.csv', 'rt')
    inputFile3 = open('Scenario0001/source/input/Data/STEO/Crude_Import_Price_Coef.csv', 'rt')
    inputFile4 = open('Scenario0001/source/input/Data/STEO/Crude_Import_Price_Breakpoints.csv', 'rt')
    inputFile5 = open('Scenario0001/source/input/Data/STEO/H_Sour_to_MarkerPrice_Ratio.csv', 'rt')

    outputFile = open('Scenario0001/source/input/Data/STEO/pySTEO_BrentPrice.csv','wb')
    writer = csv.writer(outputFile)
    writer.writerow(['TimeIdx','Price']) 

    outputFile2 = open('Scenario0001/source/input/Data/STEO/pySTEO_CrudeImportP.csv','wb')
    writer2 = csv.writer(outputFile2)
    writer2.writerow(['Crude','Step','TimeIdx','Differential'])     

    reader = csv.DictReader(inputFile)
    price_data = list(reader)
    inputFile.close()

    reader = csv.DictReader(inputFile2)
    time_IDX = list(reader)
    inputFile2.close()

    reader = csv.DictReader(inputFile3)
    price_coef = list(reader)
    inputFile3.close()

    reader = csv.DictReader(inputFile4)
    breakpoints = list(reader)
    inputFile4.close()

    reader = csv.DictReader(inputFile5)
    H_sourRatio = list(reader)
    inputFile5.close()    

    dateDict = dict((i['Date'],int(i['TimeIdx'])) for i in time_IDX) 
    # timeDict = dict((i['TimeIdx'],i['Date']) for i in time_IDX)  

    Dates    = sorted(list(set([i['Date'] for i in time_IDX])), key=int)
    TimeIdx  = sorted(list(set([int(i['TimeIdx']) for i in time_IDX])), key=int) 
    LastIdx  = max(TimeIdx)
    Overtime = range(LastIdx+1,LastIdx+11)
    TimeIdx  = TimeIdx + Overtime

    CrudeType = sorted(list(set([i['CrudeType'] for i in price_coef])))
    Steps     = sorted(list(set([i['Step'] for i in breakpoints])))

    CrudeCoeff = dict((i['CrudeType'],float(i['Coefficient'])) for i in price_coef)
    BP      = dict((i['Step'],float(i['BreakPoint'])) for i in breakpoints)    

    centerPrices = dict(((i[0],i[1]),0) for i in itertools.product(TimeIdx,CrudeType))

    for data in [x for x in price_data if x['Date'] in Dates]:

      t = dateDict[data['Date']]

      # Write out crude marker (Brent) price
      writer.writerow([t,data['Price']])      
      
      # Calculate crude import curve centerpoint prices for each crude type
      centerPrices[(t,'L_Sweet')] = float(data['Price'])
      centerPrices[(t,'H_Sour')]  = float(data['Price']) * float(H_sourRatio[0]['Ratio'])
      for c in CrudeType:
        if c.strip() != 'L_Sweet':
          centerPrices[(t,c)] = (centerPrices[(t,'H_Sour')] - CrudeCoeff[c]*centerPrices[(t,'L_Sweet')])/(1-CrudeCoeff[c])


    # Extend past time horizon at 2%
    lastPrice = centerPrices[(LastIdx,'L_Sweet')]
    for idx, t in enumerate(Overtime):

      thisprice = lastPrice*(1.02)**(idx+1)

      # Write out crude marker (Brent) price
      writer.writerow([str(t), thisprice])      
      
      # Calculate crude import curve centerpoint prices for each crude type
      centerPrices[(t,'L_Sweet')] = thisprice
      centerPrices[(t,'H_Sour')]  = thisprice * float(H_sourRatio[0]['Ratio'])
      for c in CrudeType:
        if c.strip() != 'L_Sweet':
          centerPrices[(t,c)] = (centerPrices[(t,'H_Sour')] - CrudeCoeff[c]*centerPrices[(t,'L_Sweet')])/(1-CrudeCoeff[c])


    # Calculate crude differentials across crude types for each step on the crude import supply curves
    # for d in Dates:
    #   for c in CrudeType:
    #     for s, s_2 in zip(range(0,len(Steps)-1),range(1,len(Steps))):
    #       diff = (centerPrices[(d,c)]*(1+float(breakpoints[s]['BreakPoint'])) + centerPrices[(d,c)]*(1+float(breakpoints[s_2]['BreakPoint'])))/2 - centerPrices[(d,'L_Sweet')]
    #       writer2.writerow([c,breakpoints[s]['Step'],dateDict[d],diff])
    for t in TimeIdx:
      for c in CrudeType:
        for s, s_2 in zip(range(0,len(Steps)-1),range(1,len(Steps))):
          diff = (centerPrices[(t,c)]*(1+float(breakpoints[s]['BreakPoint'])) + centerPrices[(t,c)]*(1+float(breakpoints[s_2]['BreakPoint'])))/2 - centerPrices[(t,'L_Sweet')]
          writer2.writerow([c,breakpoints[s]['Step'],t,diff])          

 
    outputFile.close()
    outputFile2.close()


def PointInRegion(boundaryfile,lat,lng):
   point = Point(float(lng), float(lat)) # longitude, latitude

   with fiona.open(boundaryfile, 'r') as boundaries:
       for f in boundaries:
         geom = shape(f['geometry'])
         if(geom.contains(point)):
            return str(f['properties']['RREG']) + '_RefReg'
            


#####################################################################
# Process STEO refinery outage report from EIA
#####################################################################
def processRefineryOutages():

    print "Processing Refinery Outage data..."

    inputFile  = open('Scenario0001/source/input/Data/STEO/EIA_RefineryOutages.csv', 'rt')
    inputFile2 = open('Scenario0001/source/input/Data/STEO/STEO_TimeIdx_Date.csv', 'rt')
    inputFile3 = open('Scenario0001/source/input/Data/STEO/Map_UnitType_Process.csv', 'rt')
    inputFile4 = open('Scenario0001/source/input/Data/STEO/STEO_RefineryCapacity.csv', 'rt')
    shapeFile  = 'refRegions.shp'   

    outputFile = open('Scenario0001/source/input/Data/STEO/pySTEO_RefineryCapacity.csv','wb')
    writer = csv.writer(outputFile)
    writer.writerow(['TimeIdx','Site_Name','RefType','Process','ExCap']) 

    reader = csv.DictReader(inputFile)
    outage_data = list(reader)
    inputFile.close()

    reader = csv.DictReader(inputFile2)
    time_IDX = list(reader)
    inputFile2.close()

    reader = csv.DictReader(inputFile3)
    UnitType_2_Process = list(reader)
    inputFile3.close()    

    reader = csv.DictReader(inputFile4)
    ref_cap = list(reader)
    inputFile4.close()    

    dateDict     = dict((i['Date'],i['TimeIdx']) for i in time_IDX)  
    UnitTypeDict = dict((i['UnitType'],i['Process']) for i in UnitType_2_Process)  

    TimeIdx  = sorted(list(set([i['TimeIdx'] for i in time_IDX])), key=int)

    outages = []
    for rec in outage_data:
      dstart     = datetime.strptime(rec['StartDate'], "%d-%b-%y")
      dend       = datetime.strptime(rec['EndDate'], "%d-%b-%y")            
      delta      = dend - dstart
      m          = dstart.month
      days_in_m  = monthrange(dstart.year, dstart.month)[1]
      datestring = dstart.strftime('%Y%m')      
      daycount   = 0
      for i in range(delta.days + 1):
        dd = dstart + timedelta(days=i)
        if dd.month != m:
          if datestring in dateDict.keys():
            d = {}
            d['TimeIdx']  = dateDict[datestring]
            d['Date']     = datestring
            d['Region']   = PointInRegion(shapeFile,rec['LATITUDE'],rec['LONGITUDE'])
            d['RefType']  = 'COKING'
            d['Process']  = UnitTypeDict[rec['UnitType']]
            d['Capacity']   = (float(daycount)/days_in_m)*float(rec['CapacityOffline'])/1000  # M bbl/day offline based on number of days out per month
            outages.append(d)

          m = dd.month
          datestring = dd.strftime('%Y%m')
          days_in_m = monthrange(dd.year, dd.month)[1] 
          daycount = 1
        elif dd==dend:
          daycount += 1
          if datestring in dateDict.keys():
            d = {}
            d['TimeIdx']  = dateDict[datestring]
            d['Date']     = datestring
            d['Region']   = PointInRegion(shapeFile,rec['LATITUDE'],rec['LONGITUDE'])
            d['RefType']  = 'COKING'
            d['Process']  = UnitTypeDict[rec['UnitType']]
            d['Capacity']   = (float(daycount)/days_in_m)*float(rec['CapacityOffline'])/1000  # M bbl/day offline based on number of days out per month
            outages.append(d)
        else:
          daycount += 1

    tuples = sorted(list(set([(m['Site_Name'], m['RefType'], m['Process']) for m in ref_cap])), key=lambda x: (x[2], x[0]))

    # Sum up outage recors by region, process, and time, subtract them from existing capacity, and write them out
    for t in TimeIdx:      
      for combo in tuples:
        # Calculate existing plus planned capacity in this time period
        basecap     = sum(float(j['ExCap']) for j in ref_cap if (j['Site_Name'],j['RefType'],j['Process'])==combo and float(j['TimeIdx'])<=float(t))        
        
        # Calculate total outages for this Region-RefType-Process combination in this time period
        totaloutage = sum(float(j['Capacity']) for j in outages if (j['Region'],j['RefType'],j['Process'])==combo and float(j['TimeIdx'])==float(t))   
        
        # Write de-rated capacities 
        writer.writerow([t,combo[0],combo[1],combo[2], max(0, basecap - totaloutage)])

   
    outputFile.close()


#####################################################################
# Main program
#####################################################################
def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage =
      """python %prog [options] <download> ...
      Process EIA API bulk JSON data for use in ST-LFMM/STEO. Optional flag '-d' indicates that you wish
      to download new bulk API files from the EIA website.
      """)
    parser.add_option("-d", "--download", help="Download new bulk API files from EIA website", action="store_true", dest="grabfiles")
    parser.add_option("-n", "--noparse", help="Skip parsing of bulk API files and prepare input from existing files", action="store_true", dest="skipparse")

    options, args = parser.parse_args(argv)

    # Download new EIA data files if requested
    if options.grabfiles:
      pullAPIdata() 
      pullCompanyLevelImports()

    # Process API data
    if not options.skipparse:
      parseJSONdata()

    # Process the STEO domestic crude production data
    PADD_CrudeReg_frac, CrudeReg_CrudeType_frac = processSTEOcrudeRep()

    # Process the EIA storage capacity data
    processStorageCap(PADD_CrudeReg_frac)

    # Process STEO petrolem product demand forecast data
    RefReg_Summer_Frac = processDemands()

    # Process the PSM inventory data
    processInventories(PADD_CrudeReg_frac,CrudeReg_CrudeType_frac,RefReg_Summer_Frac)

    # Process PSM historical import and export data
    processImportsExports(RefReg_Summer_Frac)

    # Process STEO Brent crude price forecast and create prices for the crude import supply curves
    processCrudePrices()

    # Process refinery outage data
    processRefineryOutages()




if __name__ == "__main__":
    sys.exit(main())

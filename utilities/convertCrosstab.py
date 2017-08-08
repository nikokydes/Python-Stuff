import sys
import csv
import optparse
import string

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


# Create a flat file from a cross tab file
def convertCT(inputFile,outputFile,CTcol):

    inFile  = open(inputFile, 'rt')
    reader = csv.DictReader(inFile)
    input_data = list(reader)
    inFile.close()

    outFile = open(outputFile,'wb')
    writer = csv.writer(outFile)

    # Get the unique set of column headers
    col_keys    = sorted(list(set([x for x in input_data[0].keys() if is_number(x)])))
    col_headers = sorted(list(set([x for x in input_data[0].keys() if not is_number(x)])))

    if len(col_keys)==0:
    	col_headers = sorted(list(set([x for x in input_data[0].keys() if x.strip()!='label'])))
    	writer.writerow(['ColumnLabel','RowLabel','Value'])
    	for i in input_data:	    	
	        for j in col_headers:
	            if i[j].strip(): 
	                yy = [j] + [i['label']] + ["{:.10f}".format(float(i[j]))]
	                writer.writerow(yy) 	                

	else:
	    writer.writerow(col_headers + [CTcol,'Value'])

	    for i in input_data:
	        xx = [i[x] for x in col_headers]
	        for j in col_keys:
	            if i[j].strip(): 
	                yy = xx + [j] + ["{:.10f}".format(float(i[j]))]
	                writer.writerow(yy)    

    outFile.close()


# Create a cross tab file from a flat file
def createCT(inputFile,outputFile,sourceHeaders):

    inFile  = open(inputFile, 'rt')
    reader = csv.DictReader(inFile)
    fileheaders = reader.fieldnames
    input_data = list(reader)
    inFile.close()

    if not sourceHeaders:
        if len(fileheaders)!=3:
            print "ERROR: Headers not specified and input file does not have exactly 3 columns, exiting.."
            sys.exit()
        else:
            h = fileheaders
    else:
        if set(sourceHeaders).issubset(fileheaders):
            h = sourceHeaders
        else:
            print "ERROR: Specified headers do not match the ones in the input file, exiting.."
            print sourceHeaders,fileheaders
            sys.exit()            

    outFile = open(outputFile,'wb')
    writer = csv.writer(outFile)

    # Get the unique sets of index values
    rowvars = sorted(list(set([m[h[0]] for m in input_data])))
    colvars = sorted(list(set([m[h[1]] for m in input_data])))

    writer.writerow([h[0]]+colvars)
    for i in rowvars:
        thisrow = []
        for j in colvars:
            thisrow.append(next(("{:.10f}".format(float(x[h[2]])) for x in input_data if x[h[1]]==j and x[h[0]]==i),0))

        writer.writerow([i]+thisrow)


    outFile.close()


#####################################################################
# Main program
#####################################################################
def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage =
      """python %prog [options] <download> ...
      Convert a CSV in crosstab format to a flat file format. First column MUST have header "label".
      """)
    parser.add_option("-i", "--input", help="Name of input CSV file in crosstab format", default=None)
    parser.add_option("-o", "--output", help="Name of output CSV file", default=None)
    parser.add_option("-c", "--CTcol", help="Label of the crosstab column set (i.e. year)", default=None)
    parser.add_option("-f", "--flat2CT", help="Convert from flat file to cross tab", action="store_true", dest="flat2CT")
    parser.add_option("-l", "--labels", help="Header labels to pull data from in input CSV (row,col,value)", default=None)

    options, args = parser.parse_args(argv)

    if options.labels:
        sourceHeaders = options.labels.split(',')
        if len(sourceHeaders)!=3:
            print "ERROR: Header list must have have exactly 3 columns if specified, exiting.."
            sys.exit()
    else:
        sourceHeaders = []

    if options.CTcol:
        CTcol = options.CTcol.trim()
    else:
        CTcol = 'year'
 
    # Download new EIA data files if requested
    if options.input and options.output:
        if options.flat2CT:
            createCT(options.input,options.output,sourceHeaders)
        else:
            convertCT(options.input,options.output,CTcol)
    else:
        print "Both an input and output file must be specified, exiting.."


if __name__ == "__main__":
    sys.exit(main())

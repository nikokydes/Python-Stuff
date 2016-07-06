import sys
import csv
import optparse
import string


# Create a cross tab file from a flat file
def colonToCSV(inputFile,outputFile,headerFile):

    inFile  = open(inputFile, 'rt')
    reader  = csv.reader(inFile, delimiter=':')
    outFile = open(outputFile, 'wb')
    writer  = csv.writer(outFile)

    if len(headerFile)>0:
        h       = open(headerFile, 'rt')
        hread   = csv.reader(h)
        headers = hread.next()
        h.close()
        writer.writerow(headers)

    for row in reader:
        writer.writerow(row)

    inFile.close()
    outFile.close()


#####################################################################
# Main program
#####################################################################
def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage =
      """python %prog [options] <download> ...
      Convert a colon-delimited file to a CSV.
      """)
    parser.add_option("-i", "--input", help="Name of input colon-delimited file", default=None)
    parser.add_option("-o", "--output", help="Name of output CSV file", default=None)
    parser.add_option("-d", "--headers", help="Name of CSV file containing headers", default=None)

    options, args = parser.parse_args(argv)

    if options.headers:
        headfile = options.headers
    else:
        headfile = []

    if options.input and options.output:
        colonToCSV(options.input,options.output,headfile)
    else:
    	print "Both an input and output file must be specified, exiting.."


if __name__ == "__main__":
    sys.exit(main())

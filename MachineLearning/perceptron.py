#!python2

import sys
import csv
from numpy import *
import pcn_logic_eg


def main(argv=None):
	if argv is None:
		argv = sys.argv

	

	inputs = array([[0,0],[0,1],[1,0],[1,1]])
	targets = array([[0],[1],[1],[1]])

	p = pcn_logic_eg.pcn(inputs,targets)
	p.pcntrain(inputs,targets,0.25,6)

	inputs_bias = concatenate((-ones((shape(inputs)[0],1)),inputs),axis=1)
	print p.pcnfwd(inputs_bias)




if __name__ == "__main__":
    sys.exit(main())
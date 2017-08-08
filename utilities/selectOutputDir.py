#!python2

if __name__ == "__main__":
        from glob import glob

        # Folders must have the pattern aeo[1-9][0-9][a-zA-Z]*
        paths = sorted(list(set(glob('out_Sens1/out_Misc_reserv*/'))))
        
        def getUserInput():
                print "Output directories found:"
                i = 0
                for version in paths:
                        i += 1
                        print "({}) {}".format(i, version)
                user_input = raw_input("Enter the number of your selected output directory :  ")

                try:
                        val = int(user_input)
                except ValueError:
                        print(" ")
                        print("Enter the number of your selection only. [1,2,3, etc]")
                if (user_input.isdigit() and (val <= len(paths))):
                        return val
                return 0


        def main():
                print "Choose output directory to process"
                val = 0
                while (val < 1):
                        val = getUserInput()
                        
                print "You chose ({}) {}".format(val, paths[val-1])
            
                raw_input("Press <ENTER> to close.")

        main()


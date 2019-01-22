#!python3

"""
A restaurant recommendation system.

Here are some example dictionaries.  These correspond to the information in
restaurants_small.txt.

Restaurant name to rating:
# dict of {str: int}
{'Georgie Porgie': 87,
 'Queen St. Cafe': 82,
 'Dumplings R Us': 71,
 'Mexican Grill': 85,
 'Deep Fried Everything': 52}

Price to list of restaurant names:
# dict of {str, list of str}
{'$': ['Queen St. Cafe', 'Dumplings R Us', 'Deep Fried Everything'],
 '$$': ['Mexican Grill'],
 '$$$': ['Georgie Porgie'],
 '$$$$': []}

Cuisine to list of restaurant names:
# dict of {str, list of str}
{'Canadian': ['Georgie Porgie'],
 'Pub Food': ['Georgie Porgie', 'Deep Fried Everything'],
 'Malaysian': ['Queen St. Cafe'],
 'Thai': ['Queen St. Cafe'],
 'Chinese': ['Dumplings R Us'],
 'Mexican': ['Mexican Grill']}

With this data, for a price of '$' and cuisines of ['Chinese', 'Thai'], we
would produce this list:

    [[82, 'Queen St. Cafe'], [71, 'Dumplings R Us']]
"""

# The file containing the restaurant data.
FILENAME = 'restaurants_small.txt'



def recommend(file, price, cuisines_list):
    """(file open for reading, str, list of str) -> list of [int, str] list

    Find restaurants in file that are priced according to price and that are
    tagged with any of the items in cuisines_list.  Return a list of lists of
    the form [rating%, restaurant name], sorted by rating%.
    """

    # Read the file and build the data structures.
    # - a dict of {restaurant name: rating%}
    # - a dict of {price: list of restaurant names}
    # - a dict of {cusine: list of restaurant names}
    name_to_rating, price_to_names, cuisine_to_names = read_restaurants(file)


    # Look up the list of restaurant names for the requested price.
    names_matching_price = price_to_names[price]

    # Now we have a list of restaurants in the right price range.
    # Need a new list of restaurants that serve one of the cuisines.
    names_final = filter_by_cuisine(names_matching_price, cuisine_to_names, cuisines_list)

    # Now we have a list of restaurants that are in the right price range and serve the requested cuisine.
    # Need to look at ratings and sort this list.
    result = build_rating_list(name_to_rating, names_final)

    # We're done!  Return that sorted list.
    return result

def build_rating_list(name_to_rating, names_final):
    """ (dict of {str: int}, list of str) -> list of list of [int, str]

    Return a list of [rating%, restaurant name], sorted by rating%

    >>> name_to_rating = {'Georgie Porgie': 87,
     'Queen St. Cafe': 82,
     'Dumplings R Us': 71,
     'Mexican Grill': 85,
     'Deep Fried Everything': 52}
    >>> names = ['Queen St. Cafe', 'Dumplings R Us']
    [[82, 'Queen St. Cafe'], [71, 'Dumplings R Us']]
    """
    
    sortedList = []
    for name in names_final:
    	sortedList.append([name_to_rating[name],name])
    
    sortedList.sort(key=lambda x: x[0], reverse=True)
    return sortedList



def filter_by_cuisine(names_matching_price, cuisine_to_names, cuisines_list):
    """ (list of str, dict of {str: list of str}, list of str) -> list of str

    >>> names = ['Queen St. Cafe', 'Dumplings R Us', 'Deep Fried Everything']
    >>> cuis = 'Canadian': ['Georgie Porgie'],
     'Pub Food': ['Georgie Porgie', 'Deep Fried Everything'],
     'Malaysian': ['Queen St. Cafe'],
     'Thai': ['Queen St. Cafe'],
     'Chinese': ['Dumplings R Us'],
     'Mexican': ['Mexican Grill']}
    >>> cuisines = ['Chinese', 'Thai']
    >>> filter_by_cuisine(names, cuis, cuisines)
    ['Queen St. Cafe', 'Dumplings R Us']
    """

    newName = []
    for c in cuisines_list:
        for name in names_matching_price:
            if name in cuisine_to_names[c]:
                newName.append(name)

    return list(set(newName))


def read_restaurants(file):
    """ (file) -> (dict, dict, dict)

    Return a tuple of three dictionaries based on the information in the file:

    - a dict of {restaurant name: rating%}
    - a dict of {price: list of restaurant names}
    - a dict of {cusine: list of restaurant names}
    """

    # Open the input file
    input_file = open(file,'r')

    # Define the return dictionaries
    name_to_rating = {}
    price_to_names = {'$': [], '$$': [], '$$$': [], '$$$$': []}
    cuisine_to_names = {}    

    # Read in each block of data and fill in the dictionaries
    i = 0
    for count,line in enumerate(input_file):
        i += 1
        # Read in the data based on which line in the block it is
        if   i == 1:
            thisname = line.strip()
        elif i == 2:
            name_to_rating[thisname] = int(line.split('%')[0])
        elif i == 3:
            price_to_names[line.strip()].append(thisname)
        elif i == 4:
            these_cuisines = line.split(',')
            for j in these_cuisines:
                jstripped = j.strip()
                if jstripped in cuisine_to_names.keys():
                    cuisine_to_names[jstripped].append(thisname)
                else:
                    cuisine_to_names[jstripped] = [thisname]
        elif i==5:
            i = 0
                
    # Close the input file
    input_file.close()

    return name_to_rating, price_to_names, cuisine_to_names



##print(recommend(FILENAME,'$',['Chinese', 'Thai']))

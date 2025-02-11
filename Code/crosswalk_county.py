import pandas as pd
import geopandas as gpd
import os
from os.path import join, split
import time
import numpy as np

path = split("/Users/taochen/Library/CloudStorage/Dropbox/Bankruptcy Law/data/NHGISEGLP_Crosswalk/Code/")[0]
root = split(path)[0]

os.chdir(path)

# Setting up the dataframe
master_df = gpd.GeoDataFrame()

# The 2010 shape file is slightly different (column names), so coding in a fix
# Note: I remove Puerto Rico from the 2010 shapefile
def append_0(string):
    return string + '0'

cw = pd.read_csv('state_name_cw.csv')

# Reading in states formally a state indicator
states = pd.read_csv('states_union.csv')

end_year = '1990'

# Reading the end year
# If you want to use a different end year, change appropriate strings
# and variable names
os.chdir(join(root, "Shapefiles", "nhgis0001_shapefile_tl2000_us_county_" + end_year))
shp_end = gpd.GeoDataFrame.from_file('US_county_' + end_year + '.shp')

cols = shp_end.columns
new_cols_end = []
for col in cols:
    if col != 'geometry':
        new_cols_end.append(col + '_' + end_year)
    else:
        new_cols_end.append(col)

shp_end.columns = new_cols_end

# Looping through other years
other_years = ['1830', '1840', '1850', '1860', '1870', '1880', '1890', '1900', '1910', '1920', '1930', '1990']
other_years.remove(end_year)

all_dfs = []  # List to collect all dataframes for concatenation

for year in other_years:
    start = time.time()  # For testing purposes

    # Reading in shapefiles
    os.chdir(join(root, "Shapefiles", "nhgis0001_shapefile_tl2000_us_county_" + year))
    shp = gpd.GeoDataFrame.from_file('US_county_' + year + '.shp')

    shp['Year'] = year
    shp['area_base'] = shp.area

    # Intersecting
    temp = gpd.overlay(shp, shp_end, how='intersection')

    # Computing weights
    temp['area'] = temp.area
    temp['weight'] = temp['area'] / temp['area_base']

    # Keeping only relevant variables
    temp = temp[['Year', 'NHGISST', 'NHGISCTY', 'STATENAM', 'NHGISNAM', 'ICPSRST', 'ICPSRCTY',
                 'area_base', 'NHGISST_' + end_year, 'NHGISCTY_' + end_year, 'STATENAM_' + end_year, 'NHGISNAM_' + end_year, 'ICPSRST_' + end_year, 'ICPSRCTY_' + end_year,
                 'area', 'weight']]

    temp = temp[temp['area'] > 10]

    # Renormalizing weights
    reweight = temp.groupby(['NHGISCTY', 'NHGISST'])['weight'].sum().reset_index()
    reweight['new_weight'] = reweight['weight']
    reweight = reweight.drop('weight', axis=1)

    temp = temp.merge(reweight, left_on=['NHGISCTY', 'NHGISST'], right_on=['NHGISCTY', 'NHGISST'])
    temp['weight'] = temp['weight'] / temp['new_weight']

    temp = temp.drop('new_weight', axis=1)

    # Making an indicator if the state is in the union
    states_year = states[states[year] == 1]['State']
    temp['US_STATE'] = 0
    temp.loc[temp['STATENAM'].isin(states_year.apply(str.strip)), 'US_STATE'] = 1

    # Collecting dataframes for concatenation
    all_dfs.append(temp)

    print(year, time.time() - start)

# Concatenating all dataframes
master_df = pd.concat(all_dfs, ignore_index=True)

# Saving output
os.chdir(path)
output_filename = 'county_crosswalk_endyr_' + end_year + '.csv'
master_df.to_csv(output_filename, index=False)

# Uncomment to auto-open
# os.system(output_filename)

#-------------------------------------------------------------
# Name:       Map Service Download
# Purpose:    Downloads the data used in a map service layer by querying the json
# and converting to a feature class.
# Author:     Shaun Weston (shaun.weston@splicegroup.co.nz)
# Created:    14/08/2013
# Copyright:   (c) Splice Group
# ArcGIS Version:   10.1/10.2
# Python Version:   2.7
#--------------------------------

# Import modules and enable data to be overwritten
import os
import sys
import datetime
import string
import json
import urllib
import arcpy
arcpy.env.overwriteOutput = True
    
# Pass parameters to function
def gotoFunction(logFile,mapService,featureClass): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
    try:
        #--------------------------------------------Logging--------------------------------------------#        
        #Set the start time
        setdateStart = datetime.datetime.now()
        datetimeStart = setdateStart.strftime("%d/%m/%Y - %H:%M:%S")
        # Open log file to set start time
        with open(logFile, "a") as f:
            f.write("---" + "\n" + "Map service download process started at " + datetimeStart)
        #-----------------------------------------------------------------------------------------------#

        # Create map service query
        arcpy.AddMessage("Getting JSON from map service...")
        mapServiceQuery = mapService + "/query?text=&geometry=&geometryType=&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&objectIds=&where=1%3D1&time=&returnCountOnly=false&returnIdsOnly=false&returnGeometry=true&maxAllowableOffset=&outSR=&outFields=*&f=pjson"
        urlResponse = urllib.urlopen(mapServiceQuery);
        # Get json for feature returned
        mapServiceQueryJSONData = json.loads(urlResponse.read())
              
        # Get the geometry and create temporary feature class
        arcpy.AddMessage("Converting JSON to feature class...")
        count = 0
        while (len(mapServiceQueryJSONData["features"]) > count): 
            GeometryJSON = mapServiceQueryJSONData["features"][count]["geometry"]
            # Add spatial reference to geometry
            SpatialReference = mapServiceQueryJSONData["spatialReference"]["wkid"]
            GeometryJSON["spatialReference"] = {'wkid' : SpatialReference}
            Geometry = arcpy.AsShape(GeometryJSON, "True")
            # If on the first record
            if (count == 0):
                # Create new feature class
                arcpy.CopyFeatures_management(Geometry, featureClass)
                # Load the attributes
                for key, value in mapServiceQueryJSONData["features"][count]["attributes"].iteritems():
                    # Add new field
                    if key.lower() <> "objectid":
                        arcpy.AddField_management(featureClass, key, "TEXT", "", "", "5000")
                        # Insert value into field
                        cursor = arcpy.UpdateCursor(featureClass)
                        for row in cursor:
                            row.setValue(key, value)
                            cursor.updateRow(row)
            else:
                # Create new feature class then load into existing
                arcpy.CopyFeatures_management(Geometry, "in_memory\TempFeature")
                # Load the attributes
                for key, value in mapServiceQueryJSONData["features"][count]["attributes"].iteritems():
                    # Add new field
                    if key.lower() <> "objectid":
                        arcpy.AddField_management("in_memory\TempFeature", key, "TEXT", "", "", "")                    
                        # Insert value into field
                        cursor = arcpy.UpdateCursor("in_memory\TempFeature")
                        for row in cursor:
                            row.setValue(key, value)
                            cursor.updateRow(row)
                arcpy.Append_management("in_memory\TempFeature", featureClass, "NO_TEST", "", "")
            count = count + 1
            arcpy.AddMessage("Loaded " + str(count) + " of " + str(len(mapServiceQueryJSONData["features"])) + " features...")
        #--------------------------------------------Logging--------------------------------------------#           
        #Set the end time
        setdateEnd = datetime.datetime.now()
        datetimeEnd = setdateEnd.strftime("%d/%m/%Y - %H:%M:%S")
        # Open log file to set end time
        with open(logFile, "a") as f:
            f.write("\n" + "Map service download process ended at " + datetimeEnd + "\n")
            f.write("---" + "\n")
        #-----------------------------------------------------------------------------------------------#        
        pass
    # If arcpy error
    except arcpy.ExecuteError:
        #--------------------------------------------Logging--------------------------------------------#            
        arcpy.AddMessage(arcpy.GetMessages(2))    
        #Set the end time
        setdateEnd = datetime.datetime.now()
        datetimeEnd = setdateEnd.strftime("%d/%m/%Y - %H:%M:%S")
        # Open log file to set end time
        with open(logFile, "a") as f:
            f.write("\n" + "Map service download process ended at " + datetimeEnd + "\n")
            f.write("There was an error: " + arcpy.GetMessages(2) + "\n")        
            f.write("---" + "\n")
        #-----------------------------------------------------------------------------------------------#
    # If python error
    except Exception as e:
        #--------------------------------------------Logging--------------------------------------------#           
        arcpy.AddMessage(e.args[0])           
        #Set the end time
        setdateEnd = datetime.datetime.now()
        datetimeEnd = setdateEnd.strftime("%d/%m/%Y - %H:%M:%S")
        # Open log file to set end time
        with open(logFile, "a") as f:
            f.write("\n" + "Map service download process ended at " + datetimeEnd + "\n")
            f.write("There was an error: " + e.args[0] + "\n")        
            f.write("---" + "\n")
        #-----------------------------------------------------------------------------------------------#             
# End of function

# This test allows the script to be used from the operating
# system command prompt (stand-alone), in a Python IDE, 
# as a geoprocessing script tool, or as a module imported in
# another script
if __name__ == '__main__':
    # Arguments are optional - If running from ArcGIS Desktop tool, parameters will be loaded into *argv
    argv = tuple(arcpy.GetParameterAsText(i)
        for i in range(arcpy.GetArgumentCount()))
    gotoFunction(*argv)      
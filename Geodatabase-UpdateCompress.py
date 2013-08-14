#-------------------------------------------------------------
# Name:       Geodatabase - Update and Compress
# Purpose:    Will compress geodatabase and update statistics.          
# Author:     Shaun Weston (shaun.weston@splicegroup.co.nz)
# Created:    07/08/2013
# Copyright:   (c) Splice Group
# ArcGIS Version:   10.1/10.2
# Python Version:   2.7
#--------------------------------

# Import modules and enable data to be overwritten
import os
import sys
import datetime
import arcpy
arcpy.env.overwriteOutput = True
    
# Pass parameters to function
def gotoFunction(logFile,geodatabase): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
    try:
        #--------------------------------------------Logging--------------------------------------------#        
        #Set the start time
        setdateStart = datetime.datetime.now()
        datetimeStart = setdateStart.strftime("%d/%m/%Y - %H:%M:%S")
        # Open log file to set start time
        with open(logFile, "a") as f:
            f.write("---" + "\n" + "Geodatabase update and compress process started at " + datetimeStart)
        #-----------------------------------------------------------------------------------------------#

        # Compress the geodatabase
        arcpy.AddMessage("Compressing the database....")
        arcpy.env.workspace = geodatabase
        arcpy.Compress_management(geodatabase)
        
        # Load in datsets to a list
        dataList = arcpy.ListTables() + arcpy.ListFeatureClasses() + arcpy.ListDatasets()
        # Load in datasets from feature datasets to the list
        for dataset in arcpy.ListDatasets("", "Feature"):
            arcpy.env.workspace = os.path.join(geodatabase,dataset)
            dataList += arcpy.ListFeatureClasses() + arcpy.ListDatasets()

        # Reset the workspace
        arcpy.env.workspace = geodatabase

        # Get the user name for the workspace
        userName = arcpy.Describe(geodatabase).connectionProperties.user.lower()

        # Remove any datasets that are not owned by the connected user.
        userDataList = [ds for ds in dataList if ds.lower().find(".%s." % userName) > -1]        

        # Execute analyze datasets
        arcpy.AddMessage("Analyzing and updating the database statistics....")
        # Note: to use the "SYSTEM" option the workspace user must be an administrator.
        arcpy.AnalyzeDatasets_management(geodatabase, "SYSTEM", dataList, "ANALYZE_BASE","ANALYZE_DELTA","ANALYZE_ARCHIVE")

        #--------------------------------------------Logging--------------------------------------------#           
        #Set the end time
        setdateEnd = datetime.datetime.now()
        datetimeEnd = setdateEnd.strftime("%d/%m/%Y - %H:%M:%S")
        # Open log file to set end time
        with open(logFile, "a") as f:
            f.write("\n" + "Geodatabase update and compress process ended at " + datetimeEnd + "\n")
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
            f.write("\n" + "Geodatabase update and compress process ended at " + datetimeEnd + "\n")
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
            f.write("\n" + "Geodatabase update and compress process ended at " + datetimeEnd + "\n")
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
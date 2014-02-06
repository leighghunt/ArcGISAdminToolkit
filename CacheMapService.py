#-------------------------------------------------------------
# Name:       Cache Map Service
# Purpose:    Caches a map service at specified scales and reports on progress. Ability to also
#             pause/resume caching at a specified time.
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    14/01/2014
# Last Updated:    14/01/2014
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   10.1+
# Python Version:   2.7
#--------------------------------

# Import modules and enable data to be overwritten
import os
import sys
import datetime
import smtplib
import arcpy
arcpy.env.overwriteOutput = True

# Set variables
logInfo = "true"
logFile = os.path.join(os.path.dirname(__file__), r"Logs\CacheMapService.log")
sendEmail = "false"
emailTo = ""
emailUser = ""
emailPassword = ""
emailSubject = ""
emailMessage = ""
output = None

# Start of main function
def mainFunction(mapService,updateMode,tileScheme): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
    try:
        # Log start
        if logInfo == "true":
            loggingFunction(logFile,"start","")

        # --------------------------------------- Start of code --------------------------------------- #
        
        # If new cache
        if updateMode == "New":
            # If tile scheme file provided
            if (len(str(tileScheme)) > 0):        
                arcpy.AddMessage("Creating new cache...")
                # Create cache folders
                arcpy.CreateMapServerCache_server(mapService, tileScheme, "PREDEFINED", "", "", "", "", "", "0 0", "", "", "0", "COMPACT")
                # Start caching process
                arcpy.ManageMapServerCacheTiles_server(mapService, "", "RECREATE_ALL_TILES", "", "", "", "WAIT")
            else:
                arcpy.AddError("Please provide a tiling scheme file for the cache...")
                
        # If existing cache to create all tiles
        if updateMode == "Existing - Recreate All Tiles":
            # Rebuild the map cache
            arcpy.AddMessage("Rebuilding cache...")
            # Start caching process            
            arcpy.ManageMapServerCacheTiles_server(mapService, "", "RECREATE_ALL_TILES", "", "", "", "WAIT")
            
        # If existing cache to create empty tiles
        if updateMode == "Existing - Recreate Empty Tiles":
            # Rebuild the map cache
            arcpy.AddMessage("Rebuilding cache...")
            # Start caching process            
            arcpy.ManageMapServerCacheTiles_server(mapService, "", "RECREATE_EMPTY_TILES", "", "", "", "WAIT")
      
        # --------------------------------------- End of code --------------------------------------- #  
            
        # If called from gp tool return the arcpy parameter   
        if __name__ == '__main__':
            # Return the output if there is any
            if output:
                arcpy.SetParameterAsText(1, output)
        # Otherwise return the result          
        else:
            # Return the output if there is any
            if output:
                return output      
        # Log start
        if logInfo == "true":
            loggingFunction(logFile,"end","")        
        pass
    # If arcpy error
    except arcpy.ExecuteError:
        # Show the message
        arcpy.AddError(arcpy.GetMessages(2))        
        # Log error
        if logInfo == "true":  
            loggingFunction(logFile,"error",arcpy.GetMessages(2))
    # If python error
    except Exception as e:
        # Show the message
        arcpy.AddError(e.args[0])          
        # Log error
        if logInfo == "true":         
            loggingFunction(logFile,"error",e.args[0])
# End of main function

# Start of logging function
def loggingFunction(logFile,result,info):
    #Get the time/date
    setDateTime = datetime.datetime.now()
    currentDateTime = setDateTime.strftime("%d/%m/%Y - %H:%M:%S")
    
    # Open log file to log message and time/date
    if result == "start":
        with open(logFile, "a") as f:
            f.write("---" + "\n" + "Process started at " + currentDateTime)
    if result == "end":
        with open(logFile, "a") as f:
            f.write("\n" + "Process ended at " + currentDateTime + "\n")
            f.write("---" + "\n")
    if result == "warning":
        with open(logFile, "a") as f:
            f.write("\n" + "Warning: " + info)               
    if result == "error":
        with open(logFile, "a") as f:
            f.write("\n" + "Process ended at " + currentDateTime + "\n")
            f.write("Error: " + info + "\n")        
            f.write("---" + "\n")
        # Send an email
        if sendEmail == "true":
            arcpy.AddMessage("Sending email...")
            # Server and port information
            smtpserver = smtplib.SMTP("smtp.gmail.com",587) 
            smtpserver.ehlo()
            smtpserver.starttls() 
            smtpserver.ehlo
            # Login with sender email address and password
            smtpserver.login(emailUser, emailPassword)
            # Email content
            header = 'To:' + emailTo + '\n' + 'From: ' + emailUser + '\n' + 'Subject:' + emailSubject + '\n'
            message = header + '\n' + emailMessage + '\n' + '\n' + info
            # Send the email and close the connection
            smtpserver.sendmail(emailUser, emailTo, message)
            smtpserver.close()                
# End of logging function     

# This test allows the script to be used from the operating
# system command prompt (stand-alone), in a Python IDE, 
# as a geoprocessing script tool, or as a module imported in
# another script
if __name__ == '__main__':
    # Arguments are optional - If running from ArcGIS Desktop tool, parameters will be loaded into *argv
    argv = tuple(arcpy.GetParameterAsText(i)
        for i in range(arcpy.GetArgumentCount()))
    mainFunction(*argv)
    

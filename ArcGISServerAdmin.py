#-------------------------------------------------------------
# Name:       ArcGIS Server Admin
# Purpose:    This script has a number of functions to make use of the server admin API.          
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    07/08/2013
# Last Updated:    07/08/2013
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   10.1+
# Python Version:   2.7
#--------------------------------

# Import modules and enable data to be overwritten
import urllib
import urllib2
import httplib
import json
import sys
import os
import datetime
import time
import arcpy
arcpy.env.overwriteOutput = True
              
# Re-usable function to get a token required for admin changes
def gentoken(server, port, adminUser, adminPass, expiration=60):
    
    query_dict = {'username':   adminUser,
                  'password':   adminPass,
                  'expiration': str(expiration),
                  'client':     'requestip'}
    
    query_string = urllib.urlencode(query_dict)
    url = "http://{}:{}/arcgis/admin/generateToken?f=json".format(server, port)
   
    try:
        token = json.loads(urllib2.urlopen(url, query_string).read())
        if "token" not in token or token == None:
            print "Failed to get token, return message from server:"
            print token['messages']
            sys.exit()
        else:
            # Return the token to the function which called for it
            return token['token']
    
    except urllib2.URLError, e:
        print "Could not connect to machine {} on port {}".format(server, port)
        print e
        sys.exit()
        

    

# Function to stop, start or delete a service.
# Requires Admin user/password, as well as server and port (necessary to construct token if one does not exist).
# stopStart = Stop|Start|Delete
# serviceList = List of services. A service must be in the <name>.<type> notation
# If a token exists, you can pass one in for use.  
def stopStartServices(server, port, adminUser, adminPass, stopStart, serviceList, token=None):    
    
    # Get and set the token
    if token is None:       
        token = gentoken(server, port, adminUser, adminPass)    
    
    if serviceList == "all":
        serviceList = getServiceList(server, port, adminUser, adminPass, token)
    else: 
        serviceList = [serviceList]
        
        
    # modify the services(s)    
    for service in serviceList:
        op_service_url = "http://{}:{}/arcgis/admin/services/{}/{}?token={}&f=json".format(server, port, service, stopStart, token)
        status = urllib2.urlopen(op_service_url, ' ').read()
        
        if 'success' in status:
            print stopStart + " successfully performed on " + service
        else: 
            print "Failed to perform operation. Returned message from the server:"
            print status
    
    return 
       
# Function to create feature class from extents queried
def generateFCExtent(server, port, adminUser, adminPass, logFC, mapService, workspace, featureClass, raster, token=None):

    millisecondsToQuery = 6048000000 # One week 
    hitDict = {}
    
    if token is None:    
        token = gentoken(server, port, adminUser, adminPass) 

    # Assign map service    
    if mapService.endswith(".MapServer"):
        pass
    else:
        mapService += ".MapServer"
    serviceURL = "/arcgis/rest/services/{0}".format( mapService.replace( ".", "/"))

    # Get Extent detail for service
    serviceURL = serviceURL + "/?Token=" + token
    fullExtent = getFullExtent(server, port, serviceURL)

    if not fullExtent:
        return

    # Construct URL to query the logs
    logQueryURL = "/arcgis/admin/logs/query"
    logFilter = "{'services': ['" + mapService + "']}"
    startTime = int(round(time.time() * 1000))
    endTime = startTime - millisecondsToQuery
      
    # Supply the log level, filter, token, and return format
    params = urllib.urlencode({'level': 'FINE', 'startTime': startTime, 'endTime': endTime,'filter': logFilter, 'token': token, 'f': 'json', 'pageSize':10000})
    
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    
    # Connect to URL and post parameters
    print "Accessing Logs..."
    httpConn = httplib.HTTPConnection(server, port)
    httpConn.request("POST", logQueryURL, params, headers)
    
    # Read response
    response = httpConn.getresponse()
    if (response.status != 200):
        httpConn.close()
        print "  Error while querying logs."
        return    
    else:
        data = response.read()
        
        # Check that data returned is not an error object
        if not assertJsonSuccess(data):
            print "  Error returned by operation. " + data
        else:
            print "  Operation completed successfully!"
        
        # Deserialize response into Python object
        dataObj = json.loads(data)
        httpConn.close()
        
        # Open Insert Cursor on output
        output = openCursor( workspace, featureClass, fullExtent[ "spatialReference"][ "wkid"])
        
        if not output:
            return
        
        # Need this variable to track number of events found for ExportMapImage call
        logEvents = 0
        
        # Need Array to hold Shape
        shapeArray = arcpy.Array()
        
        # Iterate over messages
        for item in dataObj[ "logMessages"]:
            eventDateTime = datetime.datetime.fromtimestamp( float( item[ "time"]) / 1000)
            
            if item[ "message"].startswith( "Extent:"):
                eventScale = None        # Scale
                eventInvScale = None    # Inverse-Scale
                eventWidth = None        # Width
                eventHeight = None    # Height
                
                # Cycle through message details
                for pair in item[ "message"].replace(" ", "").split( ";"):
                    if pair.count( ":") == 1:
                        key, val = pair.split( ":")
                        
                        # Pick out Extent
                        if key == "Extent" and val.count( ",") == 3:
                            # Split into ordinate values
                            MinX, MinY, MaxX, MaxY = val.split( ",")
                            MinX = float( MinX)
                            MinY = float( MinY)
                            MaxX = float( MaxX)
                            MaxY = float( MaxY)
                            
                            # Make sure extent is within range
                            if MinX > fullExtent[ "xmin"] and MaxX < fullExtent[ "xmax"] and MinY > fullExtent[ "ymin"] and MaxY < fullExtent[ "ymax"]:
                                shapeArray.add( arcpy.Point( MinX, MinY))
                                shapeArray.add( arcpy.Point( MinX, MaxY))
                                shapeArray.add( arcpy.Point( MaxX, MaxY))
                                shapeArray.add( arcpy.Point( MaxX, MinY))
                                shapeArray.add( arcpy.Point( MinX, MinY))
                        
                        # Pick out Size
                        if key == "Size" and val.count( ",") == 1:
                            eventWidth, eventHeight = val.split( ",")
                            eventWidth = float( eventWidth)
                            eventHeight = float( eventHeight)
                        
                        # Pick out Scale
                        if key == "Scale":
                            eventScale = float( val)
                            eventInvScale = 1 / eventScale
                
                # Save if Shape created
                if shapeArray.count > 0:
                    # Create new row
                    newRow = output.newRow()
                    
                    # Add Shape and Event Date
                    newRow.setValue( "Shape", shapeArray)
                    newRow.setValue( "EventDate", eventDateTime)
                    newRow.setValue( "Scale", eventScale)
                    newRow.setValue( "InvScale", eventInvScale)
                    newRow.setValue( "Width", eventWidth)
                    newRow.setValue( "Height", eventHeight)
                    
                    output.insertRow( newRow)
                    
                    # Clear out Array points
                    shapeArray.removeAll()
                    
                    logEvents += 1
        
        # Need ArcGIS Desktop Advanced and Spatial Analyst licensed
        # Create a raster layer from the extents feature class if spatial analyst extension available
        if (raster != "None"):
            print "Creating raster from feature class..."
            extentsFeatureClass = os.path.join(workspace, featureClass)
            # Convert to points
            arcpy.FeatureToPoint_management(extentsFeatureClass, "in_memory\\extentPoints", "CENTROID")         
            arcpy.Integrate_management("in_memory\\extentPoints #", "5000 Meters")
            arcpy.CollectEvents_stats("in_memory\\extentPoints", "in_memory\\extentCollectEvents")
            # Create density raster
            # Check out necessary license
            arcpy.CheckOutExtension("spatial")
            arcpy.gp.KernelDensity_sa("in_memory\\extentCollectEvents", "ICOUNT", "in_memory\\extentRaster", "50", "20000", "SQUARE_MAP_UNITS")
            # Remove values that are 0
            arcpy.gp.SetNull_sa("in_memory\\extentRaster", "in_memory\\extentRaster", os.path.join(workspace, raster), "VALUE = 0")
        print "\nDone!\n\nTotal number of events found in logs: {0}".format( logEvents)
        
        return

# Function to query service for Extent and Spatial Reference details
def getFullExtent( serverName, serverPort, serviceURL):
    # Supply the return format
    params = urllib.urlencode({'f': 'json'})
    
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    
    # Connect to URL and post parameters
    httpConn = httplib.HTTPConnection(serverName, serverPort)
    print serviceURL
    httpConn.request("POST", serviceURL, params, headers)
    
    # Read response
    response = httpConn.getresponse()
    if (response.status != 200):
        httpConn.close()
        print "Error while querying Service details."
        return
    else:
        data = response.read()
        
        # Check that data returned is not an error object
        if not assertJsonSuccess(data):
            print "Error returned by Service Query operation. " + data
        
        # Deserialize response into Python object
        dataObj = json.loads(data)
        httpConn.close()
        
        if not 'fullExtent' in dataObj:
            print "Unable to find Extent detail for '{0}'!".format( serviceURL)
            print dataObj
        elif not 'spatialReference' in dataObj[ 'fullExtent']:
            print "Unable to find Spatial Reference for '{0}'!".format( serviceURL)
            print "dataObj"
            
        else:
            return dataObj[ 'fullExtent']
    
    return

# Function to create new feature class and return an Insert Cursor, used to store map query extents.
def openCursor( workspace, featureclassName, srid):
    if not arcpy.Exists( workspace):
        print "Unable to find Workspace '{0}'...".format( workspace)
        return
    
    print "Creating output feature class..."
    arcpy.CreateFeatureclass_management( workspace, featureclassName, "POLYGON", None, None, None, srid)
    
    Featureclass = workspace + os.sep + featureclassName
    
    print "  Adding field(s)..."
    arcpy.AddField_management( Featureclass, "EventDate", "DATE", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management( Featureclass, "Scale", "DOUBLE", 19, 2, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management( Featureclass, "InvScale", "DOUBLE", 19, 12, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management( Featureclass, "Width", "LONG", 9, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management( Featureclass, "Height", "LONG", 9, None, None, None, "NULLABLE", "NON_REQUIRED")
    
    print "  Opening Insert Cursor..."
    return arcpy.InsertCursor( Featureclass)

# Function that checks that the input JSON object
# is not an error object.
def assertJsonSuccess(data):
    obj = json.loads(data)
    if 'status' in obj and obj['status'] == "error":
        print "Error: JSON object returns an error. " + str(obj)
        return False
    else:
        return True


# Function to get service stats
def generateserviceStats(server, port, adminUser, adminPass, serviceStats, textFile, token=None):      

    millisecondsToQuery = 604800000 # One week 
    hitDict = {}
    
    if token is None:    
        token = gentoken(server, port, adminUser, adminPass) 

    # Construct URL to query the logs
    logQueryURL = "/arcgis/admin/logs/query"
    startTime = int(round(time.time() * 1000))
    endTime = startTime - millisecondsToQuery
    logFilter = "{'services':'*','server':'*','machines':'*'}"
    
    params = urllib.urlencode({'level': 'FINE', 'startTime': startTime, 'endTime': endTime, 'filter':logFilter, 'token': token, 'f': 'json', 'pageSize':10000})
    
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
    
    # Connect to URL and post parameters    
    httpConn = httplib.HTTPConnection(server, port)
    httpConn.request("POST", logQueryURL, params, headers)
    
    # Read response
    response = httpConn.getresponse()
    if (response.status != 200):
        httpConn.close()
        print "Error while querying logs."
        return
    else:
        data = response.read()

        # Check that data returned is not an error object
        if not assertJsonSuccess(data):          
            print "Error returned by operation. " + data
        else:
            print "Operation completed successfully!"

        # Deserialize response into Python object
        dataObj = json.loads(data)
        httpConn.close()

        # Need these variables to calculate average draw time for an ExportMapImage call
        mapDraws = 0
        totalDrawTime = 0 
        
        # Iterate over messages        
        for item in dataObj["logMessages"]:
            
                       
            if item["message"] == "End ExportMapImage":

                elapsed = float(item["elapsed"])
                keyCheck = item["source"]

                if keyCheck in hitDict:
                    stats = hitDict[keyCheck]

                    # Add 1 to tally of hits
                    stats[0] += 1
                    
                    # Add elapsed time to total elapsed time
                    stats[1] += elapsed
                else:
                    # Add key with one hit and total elapsed time
                    hitDict[keyCheck] = [1,elapsed]

        # Open text file and write header line       
        summaryFile = open(textFile, "w")        
        header = "Service,Number of hits,Average seconds per draw\n"
        summaryFile.write(header)

        # Read through dictionary and write totals into file 
        for key in hitDict:

            # Calculate average elapsed time
            totalDraws = hitDict[key][0]
            totalElapsed = hitDict[key][1]
            avgElapsed = 0

            if totalDraws > 0:     
                avgElapsed = (1.0 * (totalElapsed / totalDraws)) #Elapsed time divided by hits

            # Construct and write the comma-separated line         
            line = key + "," + str(totalDraws) + "," + str(avgElapsed) + "\n"
            summaryFile.write(line)

        summaryFile.close()
        return
    

# Function to get all services
# Requires Admin user/password, as well as server and port (necessary to construct token if one does not exist).
# If a token exists, you can pass one in for use.  
# Note: Will not return any services in the Utilities or System folder
def getServiceList(server, port, adminUser, adminPass, token=None):   
        
    if token is None:    
        token = gentoken(server, port, adminUser, adminPass)    
    
    services = []    
    folder = ''    
    URL = "http://{}:{}/arcgis/admin/services{}?f=pjson&token={}".format(server, port, folder, token)    

    try:
        serviceList = json.loads(urllib2.urlopen(URL).read())
    except urllib2.URLError, e:
        print e
        sys.exit()

    # Build up list of services at the root level
    for single in serviceList["services"]:
        services.append(single['serviceName'] + '.' + single['type'])
     
    # Build up list of folders and remove the System and Utilities folder (we dont want anyone playing with them)
    folderList = serviceList["folders"]
    folderList.remove("Utilities")             
    folderList.remove("System")
        
    if len(folderList) > 0:
        for folder in folderList:                                              
            URL = "http://{}:{}/arcgis/admin/services/{}?f=pjson&token={}".format(server, port, folder, token)    
            fList = json.loads(urllib2.urlopen(URL).read())
            
            for single in fList["services"]:
                services.append(folder + "//" + single['serviceName'] + '.' + single['type'])                
    
    if len(services) == 0:
        print "No services found"
    else:
        print "Services on " + server +":"
        for service in services: 
            statusURL = "http://{}:{}/arcgis/admin/services/{}/status?f=pjson&token={}".format(server, port, service, token)
            status = json.loads(urllib2.urlopen(statusURL).read())
            print "  " + status["realTimeState"] + " > " + service
            
     
    return services





# Input handlers
if __name__ == "__main__": 

    args = sys.argv

    # If no arguments provided, direct to help    
    if len(args) == 1:
        print "Use '/?' for help"
    
    else:
        # If /? used, then print the help
        if args[1] == '/?':
            print "agsAdmin.exe utility provides a way to script ArcGIS Server administrative tasks."
            print "This module is built on python and compiled into an exe which you can call from command"
            print "line or a batch file. Note that all admin usernames and passwords are sent in clear text. \n\n"
            
            print "Usage:"
            print "Generate extents feature class: agsAdmin.exe server port adminUser adminPass logFC SpliceGroup/SpliceOffice.MapServer D:\Data\Temp\Scratch.gdb LogExtents None"
            print "Map service stats: agsAdmin.exe server port adminUser adminPass serviceStats D:\Data\Temp\Stats.txt"
            print "List services: agsAdmin.exe server port adminUser adminPass list"
            print "Stop a service: agsAdmin.exe server port adminUser adminPass stop Map.MapService"
            print "Start a service: agsAdmin.exe server port adminUser adminPass start Buffer.GPService"
            print "Delete a service: agsAdmin.exe server port adminUser adminPass delete Find.GeocodeServer"
            print "The 'all' keyword can be used in place of a service name to stop, start or delete all services \n"
            print "e.g. agsAdmin.exe myServer 6080 admin p@$$w0rd list"
            print "e.g. agsAdmin.exe myServer 6080 admin p@$$w0rd start ForestCover.MapService"
            print "e.g. agsAdmin.exe myServer 6080 admin p@$$w0rd stop all"
            
        # Otherwise if arguments are given    
        else:
            # If less than six arguments are provided, show error message and direct to help
            if len(args) < 6:
                print "Not enough arguments, use '/?' for help"
            else:
                # Go to function depending on what is entered
                if args[5] == "list":    
                    getServiceList(*args[1:5])        
                elif args[5] == "start" or args[5] == "stop" or args[5] == "delete":
                    stopStartServices(*args[1:7])
                elif args[5] == "logFC":    
                    generateFCExtent(*args[1:10])
                elif args[5] == "serviceStats":    
                    generateserviceStats(*args[1:7])                    
                else:
                    print "Unknown command:   " + str(args[5]) + " ,use '/?' for help"
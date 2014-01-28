#-------------------------------------------------------------
# Name:       Backup and/or Restore ArcGIS Server site
# Purpose:    Backs up and/or restores and ArcGIS server site.     
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    27/01/2014
# Last Updated:    28/01/2014
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   10.2+
# Python Version:   2.7
#--------------------------------

# Import modules and enable data to be overwritten
import os
import sys
import datetime
import json
import codecs
import smtplib
import httplib
import urllib
import urlparse
import arcpy
arcpy.env.overwriteOutput = True

# Set variables
logInfo = "false"
logFile = r""
sendEmail = "true"
emailTo = ""
emailUser = ""
emailPassword = ""
emailSubject = ""
emailMessage = ""
output = None

# Start of main function
def mainFunction(agsServerSite,username,password,backupRestore,backupFolder,backupFile,restoreReport): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
    try:
        # Log start
        if logInfo == "true":
            loggingFunction(logFile,"start","")

        # --------------------------------------- Start of code --------------------------------------- #        

        # Get the server site details
        protocol, serverName, serverPort, context = splitSiteURL(agsServerSite)

        # If any of the variables are blank
        if (serverName == None or serverPort == None or protocol == None or context == None):
            return -1

        # Add on slash to context if necessary
        if not context.endswith('/'):
            context += '/'

        # Add on admin to context if necessary   
        if not context.endswith('admin/'):
            context += 'admin/'

        # Create new site if necessary
        siteResult = createSite(serverName,username,password)

        # If site not created        
        if siteResult == -1:        
            arcpy.AddMessage("Site already created...")

        # Get token url
        tokenURL = context + "generateToken"

        # Get token
        token = getToken(serverName, serverPort, protocol, tokenURL, username, password)
    
        # If token is blank
        if token == None:
            return -1

        # If backing up site
        if (backupRestore == "Backup"):
            if (len(str(backupFolder)) > 0):            
                # Get backup url
                backupURL = context+"exportSite"

                # Setup parameters
                backupFolder = backupFolder.decode(sys.stdin.encoding or sys.getdefaultencoding()).encode('utf-8')
                params = urllib.urlencode({'token': token, 'f': 'json', 'location': backupFolder})

                arcpy.AddMessage("Backing up the ArcGIS Server site running at " + serverName + "...")

                try:
                    # Query the server
                    response, data = postToServer(serverName, serverPort, protocol, backupURL, params)
                except:
                    arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
                    return -1

                # If there is an error
                if (response.status != 200):
                    arcpy.AddError("Unable to back up the ArcGIS Server site running at " + serverName)
                    arcpy.AddError(str(data))
                    return -1
                
                if (not assertJsonSuccess(data)):
                    arcpy.AddError("Unable to back up the ArcGIS Server site running at " + serverName)
                # On successful backup
                else:
                    dataObj = json.loads(data)
                    arcpy.AddMessage("ArcGIS Server site has been successfully backed up and is available at this location: " + dataObj['location'] + "...")
            else:
                arcpy.AddError("Please define a folder for the backup to be exported to.");
            
        # If restoring site
        if (backupRestore == "Restore"):
            if (len(str(backupFile)) > 0):
                # Get restore url
                restoreURL = context + "importSite"

                arcpy.AddMessage("Beginning to restore the ArcGIS Server site running on " + serverName + " using the site backup available at: " + backupFile + "...")
                arcpy.AddMessage("This operation can take some time. You will not receive any status messages and will not be able to access the site until the operation is complete...")

                # Setup parameters
                backupFile = backupFile.decode(sys.stdin.encoding or sys.getdefaultencoding()).encode('utf-8')
                params = urllib.urlencode({'token': token, 'f': 'json', 'location': backupFile})

                try:
                    # Query the server
                    response, data = postToServer(serverName, serverPort, protocol, restoreURL, params)
                except:
                    arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
                    return -1   

                # If there is an error 
                if (response.status != 200):
                    arcpy.AddError("The restore of the ArcGIS Server site " + serverName + " failed.")
                    arcpy.AddError(str(data))
                    return -1

                if (not assertJsonSuccess(data)):
                    arcpy.AddError("The restore of the ArcGIS Server site " + serverName + " failed.")
                    arcpy.AddError(str(data))
                # On successful restore
                else:
                    # Convert the http response to JSON object
                    dataObj = json.loads(data)
                    results = dataObj['result']
                        
                    msgList = []
                    
                    restoreOpTime = ''        
                    for result in results:
                        messages = result['messages']
                        for message in messages:
                            if ('Import operation completed in ' in message['message'] and message['level'] == 'INFO' and result['source'] == 'SITE') :
                                restoreOpTime = message['message']
                                arcpy.AddMessage("ArcGIS Server site has been successfully restored. " + message['message'])
                            else:
                                msgList.append(message['message'])  
                    
                    # User wants the report generated from the restore utility to be saved to a file in addition to writing the messages to the console        
                    if (len(restoreReport) > 0):
                        try:
                            reportFile = codecs.open(os.path.join(restoreReport), 'w', 'utf-8-sig')
                            reportFile.write("Site has been successfully restored. " + restoreOpTime)
                            reportFile.write('\n\n')
                            if (len(msgList) > 0):
                                reportFile.write("Below are the messages returned from the restore operation. You should review these messages and update your site configuration as needed:")
                                reportFile.write('\n')
                                reportFile.write("-------------------------------------------------------------------------------------------------------------------------------------")
                                reportFile.write('\n')
                                count = 1
                                for msg in msgList:
                                    reportFile.write(str(count)+ "." + msg)
                                    reportFile.write('\n\n')
                                    count = count + 1
                            reportFile.close()
                            arcpy.AddMessage("A file with the report from the restore utility has been saved at: " + restoreReport) 
                        except:
                            arcpy.AddError("Unable to save the report file at: " + restoreReport + " Please verify this location is available.")
                            return                    
            else:
                arcpy.AddError("Please define a ArcGIS Server site backup file.");
            
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
        # Log end
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


# Start of create site function
def createSite(serverName,username,password):
    # Set server port
    serverPort = 6080 

    # Construct URL to create a new site
    createNewSiteURL = "/arcgis/admin/createNewSite"
        
    # Set up parameters for the request
    params = urllib.urlencode({'username': username, 'password': password, 'configStoreConnection': 
    '', 'directories': '', 'runAsync': 'false', 'f': 'json'})
    
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
  
    # Connect to URL and post parameters    
    httpConn = httplib.HTTPConnection(serverName, serverPort)
    httpConn.request("POST", createNewSiteURL, params, headers)
    
    # Read response
    response = httpConn.getresponse()
    if (response.status != 200):
        httpConn.close()
        arcpy.AddError("Error while creating the site.")
        return -1
    else:
        data = response.read()
        httpConn.close()
        
        # Check that data returned is not an error object
        if not assertJsonSuccess(data):          
            return -1
        else:
            arcpy.AddMessage("Site created successfully...")
            return
# End of create site function


# Start of split URL function 
def splitSiteURL(siteURL):
    try:
        serverName = ''
        serverPort = -1
        protocol = 'http'
        context = '/arcgis'
        # Split up the URL provided
        urllist = urlparse.urlsplit(siteURL)
        # Put the URL list into a dictionary
        d = urllist._asdict()

        # Get the server name and port
        serverNameAndPort = d['netloc'].split(":")

        # User did not enter the port number, so we return -1
        if (len(serverNameAndPort) == 1):
            serverName = serverNameAndPort[0]
        else:
            if (len(serverNameAndPort) == 2):
                serverName = serverNameAndPort[0]
                serverPort = serverNameAndPort[1]

        # Get protocol
        if (d['scheme'] is not ''):
            protocol = d['scheme']

        # Get path
        if (d['path'] is not '/' and d['path'] is not ''):
            context = d['path']

        # Return variables
        return protocol, serverName, serverPort, context  
    except:
        arcpy.AddError("The ArcGIS Server site URL should be in the format http(s)://<host>:<port>/arcgis")
        return None, None, None, None
# End of split URL function


# Start of get token function
def getToken(serverName, serverPort, protocol, tokenURL, username, password):
    params = urllib.urlencode({'username': username.decode(sys.stdin.encoding or sys.getdefaultencoding()).encode('utf-8'), 'password': password.decode(sys.stdin.encoding or sys.getdefaultencoding()).encode('utf-8'),'client': 'referer','referer':'backuputility','f': 'json'})

    try:
        response, data = postToServer(serverName, serverPort, protocol, tokenURL, params)
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
        return None    

    # If there is an error getting the token
    if (response.status != 200):
        arcpy.AddError("Error while generating the token.")
        arcpy.AddError(str(data))
        return None
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error while generating the token. Please check if the server is running and ensure that the username/password provided are correct.")
        return None
    # Token returned
    else: 
        # Extract the token from it
        token = json.loads(data)
        # Return the token
        return token['token']
# End of get token function


# Start of HTTP POST request to the server function
def postToServer(serverName, serverPort, protocol, url, params):
    # If on standard port
    if (serverPort == -1 and protocol == 'http'):
        serverPort = 80

    # If on secure port
    if (serverPort == -1 and protocol == 'https'):
        serverPort = 443
        
    if (protocol == 'http'):
        httpConn = httplib.HTTPConnection(serverName, int(serverPort))

    if (protocol == 'https'):
        httpConn = httplib.HTTPSConnection(serverName, int(serverPort))
        
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain",'referer':'backuputility','referrer':'backuputility'}
     
    # URL encode the resource URL
    url = urllib.quote(url.encode('utf-8'))

    # Build the connection to add the roles to the server
    httpConn.request("POST", url, params, headers) 


    response = httpConn.getresponse()
    data = response.read()

    httpConn.close()

    # Return response
    return (response, data)
# End of HTTP POST request to the server function


# Start of heck input JSON object function
def assertJsonSuccess(data):
    obj = json.loads(data)
    if 'status' in obj and obj['status'] == "error":
        if ('messages' in obj):
            errMsgs = obj['messages']
            for errMsg in errMsgs:
                print
                print errMsg
        return False
    else:
        return True
# End of check input JSON object function


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
    

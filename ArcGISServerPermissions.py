#-------------------------------------------------------------
# Name:       ArcGIS Server Permissions 
# Purpose:    Checks ArcGIS server service or folder for any permission changes.     
# Author:     Shaun Weston (shaun_weston@eagle.co.nz)
# Date Created:    03/05/2014
# Last Updated:    18/05/2014
# Copyright:   (c) Eagle Technology
# ArcGIS Version:   10.1/10.2
# Python Version:   2.7
#--------------------------------

# Import modules and enable data to be overwritten
import os
import sys
import datetime
import smtplib
import httplib
import json
import urllib
import urlparse
import arcpy
arcpy.env.overwriteOutput = True

# Set variables
logging = "false"
logFile = r""
sendErrorEmail = "false"
emailTo = ""
emailUser = ""
emailPassword = ""
emailSubject = ""
emailMessage = ""
output = None

# Start of main function
def mainFunction(agsServerSite,username,password,service,permissionExpecting): # Get parameters from ArcGIS Desktop tool by seperating by comma e.g. (var1 is 1st parameter,var2 is 2nd parameter,var3 is 3rd parameter)  
    try:
        # Log start
        if (logging == "true") or (sendErrorEmail == "true"):
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

        # Get token
        token = getToken(username, password, serverName, serverPort, protocol)

        # If token received
        if (token != -1):
            # Check permissions on service
            permissionsSet = checkPermissions(serverName, serverPort, protocol, service, token)
            
            # If permissions set
            if (len(permissionsSet) > 0):
                permissionsNum = 0
                
                # Iterate through permissions
                for permission in permissionsSet:
                    # If permission expecting is applied to service
                    if (permissionExpecting == permission):
                        arcpy.AddMessage(permissionExpecting + " is applied to the service or folder...")
                        # If logging
                        if (logging == "true") or (sendErrorEmail == "true"):
                            loggingFunction(logFile,"info",permissionExpecting + " is applied to the service or folder...")
                        # Add to permissions number
                        permissionsNum = permissionsNum + 1
                # If permission is not applied
                if (permissionsNum == 0):
                    arcpy.AddWarning(permissionExpecting + " is not applied to the service or folder...")
                    # If logging
                    if (logging == "true") or (sendErrorEmail == "true"):
                        loggingFunction(logFile,"error",permissionExpecting + " is not applied to the service or folder...")
                        sys.exit()                    
            else:
                arcpy.AddWarning("No permissions set to the service or folder...")
                # If logging
                if (logging == "true") or (sendErrorEmail == "true"):
                    loggingFunction(logFile,"warning","No permissions set to the service or folder...")               
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
        if (logging == "true") or (sendErrorEmail == "true"):
            loggingFunction(logFile,"end","")        
        pass
    # If arcpy error
    except arcpy.ExecuteError:
        # Show the message
        arcpy.AddError(arcpy.GetMessages(2))        
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):
            loggingFunction(logFile,"error",arcpy.GetMessages(2))
    # If python error
    except Exception as e:
        # Show the message
        arcpy.AddError(e.args[0])          
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error",e.args[0])
# End of main function


# Start of check permissions function
def checkPermissions(serverName, serverPort, protocol, service, token):
    params = urllib.urlencode({'token': token, 'f': 'json'})

    # Construct URL to get the service status
    url = "/arcgis/admin/services/" + service + "/permissions"

    # Post to the server
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error","Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
            sys.exit()
        return -1

    # If there is an error
    if (response.status != 200):
        arcpy.AddError("Error getting checking permissions.")
        arcpy.AddError(str(data))
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error","Error checking permissions.")
            sys.exit()
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error checking permissions. Please check if the server is running and ensure that the username/password provided are correct.")
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error","Error checking permissions. Please check if the server is running and ensure that the username/password provided are correct.")  
            sys.exit()
        return -1
    # On successful query
    else: 
        dataObject = json.loads(data)
        permissionGroupsApplied = []

        # Iterate through permission groups
        for permission in dataObject['permissions']:
            # Add permission to list
            permissionGroupsApplied.append(permission['principal'])
        return permissionGroupsApplied
# End of check permissions function


# Start of get token function
def getToken(username, password, serverName, serverPort, protocol):
    params = urllib.urlencode({'username': username.decode(sys.stdin.encoding or sys.getdefaultencoding()).encode('utf-8'), 'password': password.decode(sys.stdin.encoding or sys.getdefaultencoding()).encode('utf-8'),'client': 'referer','referer':'backuputility','f': 'json'})
           
    # Construct URL to get a token
    url = "/arcgis/tokens/generateToken"
        
    try:
        response, data = postToServer(serverName, serverPort, protocol, url, params)
    except:
        arcpy.AddError("Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error","Unable to connect to the ArcGIS Server site on " + serverName + ". Please check if the server is running.")
            sys.exit()
        return -1    
    # If there is an error getting the token
    if (response.status != 200):
        arcpy.AddError("Error while generating the token.")
        arcpy.AddError(str(data))
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error","Error while generating the token.")
            sys.exit()
        return -1
    if (not assertJsonSuccess(data)):
        arcpy.AddError("Error while generating the token. Please check if the server is running and ensure that the username/password provided are correct.")
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error","Error while generating the token. Please check if the server is running and ensure that the username/password provided are correct.")
            sys.exit()
        return -1
    # Token returned
    else:
        # Extract the token from it
        dataObject = json.loads(data)

        # Return the token if available
        if "error" in dataObject:
            arcpy.AddError("Error retrieving token.")
            # Log error
            if (logging == "true") or (sendErrorEmail == "true"):       
                loggingFunction(logFile,"error","Error retrieving token.")
                sys.exit()
            return -1        
        else:
            return dataObject['token']
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
        # Log error
        if (logging == "true") or (sendErrorEmail == "true"):       
            loggingFunction(logFile,"error","The ArcGIS Server site URL should be in the format http(s)://<host>:<port>/arcgis")
            sys.exit()
        return None, None, None, None
# End of split URL function


# Start of status check JSON object function
def assertJsonSuccess(data):
    obj = json.loads(data)
    if 'status' in obj and obj['status'] == "error":
        if ('messages' in obj):
            errMsgs = obj['messages']
            for errMsg in errMsgs:
                arcpy.AddError(errMsg)
                # Log error
                if (logging == "true") or (sendErrorEmail == "true"):       
                    loggingFunction(logFile,"error",errMsg)
            sys.exit()
        return False
    else:
        return True
# End of status check JSON object function


# Start of logging function
def loggingFunction(logFile,result,info):
    #Get the time/date
    setDateTime = datetime.datetime.now()
    currentDateTime = setDateTime.strftime("%d/%m/%Y - %H:%M:%S")
    # Open log file to log message and time/date
    if (result == "start") and (logging == "true"):
        with open(logFile, "a") as f:
            f.write("---" + "\n" + "Process started at " + currentDateTime)
    if (result == "end") and (logging == "true"):
        with open(logFile, "a") as f:
            f.write("\n" + "Process ended at " + currentDateTime + "\n")
            f.write("---" + "\n")
    if (result == "info") and (logging == "true"):
        with open(logFile, "a") as f:
            f.write("\n" + "Info: " + str(info))              
    if (result == "warning") and (logging == "true"):
        with open(logFile, "a") as f:
            f.write("\n" + "Warning: " + str(info))               
    if (result == "error") and (logging == "true"):
        with open(logFile, "a") as f:
            f.write("\n" + "Process ended at " + currentDateTime + "\n")
            f.write("Error: " + str(info) + "\n")        
            f.write("---" + "\n")
    if (result == "error") and (sendErrorEmail == "true"):            
        # Send an email
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
    

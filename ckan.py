import json 
import pandas as pd
import urllib.request
import csv
import ast
from html.parser import HTMLParser
import decimal
import ssl
import re
import sys
import os

######################################

### Manual items to change!

## set the date download of the older and newer jsons
ActionDate = '20200915'
PreviousActionDate = '20200821'

## names of the main directory containing folders named "jsons" and "reports"
## Windows:
directory = r'C:\Users\Zhouy\Documents\GitHub\ckan-metadata'
## MAC or Linux:
## directory = r'C:/Users/Zhouy/Documents/GitHub/ckan-metadata'

## list of metadata fields from the DCAT json schema for open data portals desired in the final report
fieldnames = ['Title', 'Alternative Title', 'Description', 'Language', 'Creator', 'Publisher', 'Genre',
              'Subject', 'Keyword', 'Date Issued', 'Temporal Coverage', 'Date Range', 'Solr Year', 'Spatial Coverage',
              'Bounding Box', 'Type', 'Geometry Type', 'Format', 'Information', 'Download', 'MapServer', 
              'FeatureServer', 'ImageServer', 'HTML', 'Image', 'Identifier', 'Provenance', 'Code', 'Is Part Of', 'Status',
              'Accrual Method', 'Date Accessioned', 'Rights', 'Access Rights', 'Suppressed', 'Child']

## list of fields to use for the deletedItems report
delFieldsReport = ['identifier', 'resourceName', 'landingPage']
# delFieldsReport = ['resourceName', 'landingPage']

## list of fields to use for the portal status report
# statusFieldsReport = ['total', 'new_items', 'deleted_items']
#######################################
newResource = directory + '\\resource\\resource_%s.csv' % (ActionDate)
oldResource = directory + '\\resource\\resource_%s.csv' % (PreviousActionDate)
searchurl = 'https://gisdata.mn.gov/api/3/action/package_show?id='
packageurl = 'https://gisdata.mn.gov/api/3/action/package_list'
landingurl = 'https://gisdata.mn.gov/dataset/'

### function to removes html tags from text
class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True        
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def cleanData(value):
    fieldvalue = strip_tags(value)
    return fieldvalue

################    Status Report   ###################### 

### function that prints metadata elements from the dictionary to a csv file (portal_status_report) 
### with as specified fields list as the header row. 
# def printReport(report, fields, dictionary):
#     with open(report, 'w', newline='', encoding='utf-8') as f:
#         csvout = csv.DictWriter(f, fields)
#         csvout.writeheader()
#         csvout.writerow(dictionary)

###########################################################
        
### similar to the function above but from the list to allNewItems csv files      
def printNewItemReport(report, fields, datalist):
    with open(report, 'w', newline='', encoding='utf-8') as f:
        csvout = csv.writer(f)
        csvout.writerow(fields)
        for i in datalist:
            csvout.writerow(i)

### similar to the function above but from the list to allDeletedItems csv files
def printDeletedItemReport(report, fields, datalist):
    with open(report, 'w', newline='', encoding='utf-8') as f:
        csvout = csv.writer(f)
        csvout.writerow(fields)
        csvout.writerows(zip(datalist[0], datalist[1], datalist[2]))          

### saves a copy of the all resource names json using the CKAN API 'package_list'
with open('package_list.json', 'w') as f:
    data = urllib.request.urlopen(packageurl).read()
    packageList = json.loads(data.decode('utf-8'))
    json.dump(packageList, f)

### converts the json file generated above into csv file(resource.csv)
portalDic = {}
result = []
with open('package_list.json') as f:
    data = json.load(f)
    for i in data['result']:
        result.extend([i])

portalDic['result'] = result
pd.DataFrame(portalDic).to_csv(newResource, index=False)

### function that makes a list of all resource names
def getResources(resource):
    colname = ['result']
    data = pd.read_csv(resource, names=colname)
    resultList = data.result.tolist()
    return resultList


oldList = getResources(oldResource)
newList = getResources(newResource)
   
### function that compares resource names in the older list with those in the new list 
### returns a nested list: newItems list and deletedItems list
### [[newResource1, newResource2, ...], [deletedResource1, deletedResource2, ...]]
def returnNotMatches(old, new):
    oldResource = set(old)
    newResource = set(new)
    return [list(newResource - oldResource), list(oldResource - newResource)]

newItems = returnNotMatches(oldList, newList)[0]
deletedItems = returnNotMatches(oldList, newList)[1]

### functions that returns a list of URLs representing deleted resource to be used for deletedItems report
deletedurl = []
def getURL(items, url):
    for item in items:
        downloadurl = searchurl + item
        url.extend([downloadurl])
    return url

deletedurl = getURL(deletedItems, deletedurl)

### function that returns a list of selected metadata elements (metadata) for each new resources(newitem)
### This includes blank fields '' for columns that will be filled in manually later. 
def metadataNewItems(newdata):    
    metadata = []
    
    title = ''
    alternativeTitle = newdata['result']['title']
        
    description = cleanData(newdata['result']['notes'])
    ### Remove newline, whitespace, defalut description and replace singe quote, double quote 
    if description == '{{default.description}}':
        description = description.replace('{{default.description}}', '')
    else:
        description = re.sub(r'[\n]+|[\r\n]+',' ', description, flags=re.S)
        description = re.sub(r'\s{2,}' , ' ', description)
        description = description.replace(u'\u2019', "'").replace(u'\u201c', '\"').replace(u'\u201d', '\"').replace(u'\u00a0', '').replace(u'\u00b7', '').replace(u'\u2022', '').replace(u'\u2013','-').replace(u'\u200b', '')

    language = 'English'  
    
    publisher = ''
    spatialCoverage = ''
    index = 0
    extras = newdata['result']['extras']
    for dictionary in extras:
        if dictionary['key'] == 'dsOriginator':
            creator = dictionary['value']
            
            ## if Creator field contains keywork 'County', extract the county name to fill in Publisher and Spatial Coverage field
            ## otherwise, autofill both fileds with 'Minnesota'
            index = creator.find('County')
            if index != -1:
                publisher = creator[: index + 6]
                spatialCoverage = publisher + ', Minnesota|Minnesota'
            else:
                publisher = 'State of Minnesota'
                spatialCoverage = 'Minnesota'
                            
    format_types = []
    genre = ''
    formatElement = ''
    typeElement = ''
    downloadURL =  ''
    geometryType = ''
    featureServer = ''
    webService = ''
    html = ''
    previewImg = ''
    
    distribution = newdata['result']['resources']
    for dictionary in distribution:
        try:
            ### if one of the distributions is a shapefile, change genre/format and get the downloadURL
            format_types.extend([dictionary['format']])
            if dictionary['format'] == 'SHP':
                genre = 'Geospatial data'
                formatElement = 'Shapefile'
                downloadURL = dictionary['url']
                typeElement = 'Dataset'
                geometryType = 'Vector'
                
                
            ### if one of the distributions is WMS, and it is taged as 'aerial photography'
            ### change genre, type, and format to relate to imagery
            if dictionary['format'] == 'WMS':
                tags = newdata['result']['tags']
                for tag in tags:
                    if tag['display_name'] == 'aerial photography':                        
                        genre = 'Aerial imagery'
                        formatElement = 'Imagery'
                        downloadURL = dictionary['url']
                        typeElement = 'Image|Service'
                        geometryType = 'Imagery'
                        
            ### saves the url if the dataset has Webservice format         
            if dictionary['format'] == 'ags_mapserver':
                webService = dictionary['url']
                
            ### saves the metadata page
            if dictionary['format'] == 'HTML':
                html = dictionary['url']   
            
            ### saves the thumbnail iamge
            if dictionary['format'] == 'JPEG':
                previewImg = dictionary['url']    
                
        ### if the distribution section of the metadata is not structured in a typical way
        except:
            genre = ''
            formatElement = ''
            typeElement = ''
            downloadURL =  ''
            
            continue
                                                
    ### if the item has both a Shapefile and Webservice format, change type                               
    if 'ags_mapserver' in format_types:
        if 'SHP' in format_types:
            typeElement = 'Dataset|Service'
    
    ### extracts the bounding box 
    try:
        bbox = []
        spatial = ''
        extra_spatial = newdata['result']['extras']
        for dictionary in extra_spatial:
            if dictionary['key'] == 'spatial':
                spatialList = ast.literal_eval(dictionary['value'].split(':[')[1].split(']}')[0])
                coordmin = spatialList[0]
                coordmax = spatialList[2]
                coordmin.extend(coordmax)
                typeDmal = decimal.Decimal
                fix3 = typeDmal("0.001")
                for coord in coordmin:
                    coordFix = typeDmal(coord).quantize(fix3)
                    bbox.extend([str(coordFix)])
                    spatial = ','.join(bbox)            
    except:
        spatial = ''     
        
    try:
        subject = ''
        groups_subject = newdata['result']['groups']
        if len(groups_subject) != 0:
            subject = groups_subject[0]['display_name'].replace('+', 'and')
    except:
        subject = ''
    
    keyword_list = []
    keyword = newdata['result']['tags']
    for dictionary in keyword:
        keyword_list.extend([dictionary['display_name']])
    keyword_list = ','.join(keyword_list).replace(',', '|')
    
    dateIssued = newdata['result']['metadata_created']
    temporalCoverage = ''
    dateRange = ''
    solrYear = ''
    
    information = landingurl + newdata['result']['name']
    identifier = newdata['result']['id']
    
    featureServer = ''
    mapServer = ''
    imageServer = ''
    
    ### specifies the Webservice type by querying the webService string    
    try:
        if 'FeatureServer' in webService:
            featureServer = webService
        if 'MapServer' in webService:
            mapServer = webService
        if 'ImageServer' in webService:
            imageServer = webService
    except:
            print(identifier)
    
    provenance = 'Minnesota'
    portalName = '05a-01'
    isPartOf = '05a-01'
    
    status = 'Active'
    accuralMethod = 'CKAN'
    dateAccessioned = ''
                
    rights = 'Public'               
    accessRights = ''
    suppressed = 'FALSE'
    child = 'FALSE'
    
    metadataList = [title, alternativeTitle, description, language, creator, publisher,
                    genre, subject, keyword_list, dateIssued, temporalCoverage,
                    dateRange, solrYear, spatialCoverage, spatial, typeElement, geometryType,
                    formatElement, information, downloadURL, mapServer, featureServer,
                    imageServer, html, previewImg, identifier, provenance, portalName, isPartOf, status,
                    accuralMethod, dateAccessioned, rights, accessRights, suppressed, child]
    
    ### checks the genre of resource: if it is neither 'Geospatial data' nor 'Aerial imagery', create a empty list
    for i in range(len(metadataList)):
        if metadataList[6] != '':
            metadata = metadataList
        else: 
            continue
    
    return metadata
        
All_New_Items = []
withEmpty = []
All_Deleted_Items = []


### for each new resource in the csv list, saves a copy of the json to be used for the next round of comparison/reporting
for item in newItems:
    newjson = directory + '\\jsons\\%s_%s.json' % (item, ActionDate)
    with open(newjson, 'w') as f:
        newurl = searchurl + item
        try:
            data = urllib.request.urlopen(newurl).read()
            newitem = json.loads(data.decode('utf-8'))
            json.dump(newitem, f)
            print(item)
        except ssl.CertificateError as e:
            print('Resource URL does not exist: ' + newurl)
            break
        
        ### returns a nested list containg empty list, which means this resource's genre is neither 'Geospatial data' nor 'Aerial imagery'
        withEmpty.extend([metadataNewItems(newitem)])
        
### creates a nested list of metadata elements for each resource 
### (to be used printing the combined report) 
### i.e. [[metadataElement1, metadataElement2, ... ], [metadataElement1, metadataElement2, ... ]]
### empty list in the newitem list needs to be removed
### check if there is any new or deleted resource
All_New_Items = [x for x in withEmpty if x != []]
try:
    newitem
except NameError:
    print('There is no new resource')
else:
    All_New_Items.extend([metadataNewItems(newitem)])

if deletedItems:
    All_Deleted_Items = [[None]*len(deletedItems), deletedItems, deletedurl]
else:
    print('There is no deleted resource')
    sys.exit()

################    Status Report   ###################### 
    
### create a dictionary of information about number of resources (total, new, and deleted)
# Status_Report = {}
# Status_Report['total'] = len(result)
# Status_Report['new_items'] = len(newItems)
# Status_Report['deleted_items'] = len(deletedItems)
# reportStatus = directory + "\\reports\\portal_status_report_%s.csv" % (ActionDate)
# printReport(reportStatus, statusFieldsReport, Status_Report)

###########################################################

### prints a csv spreadsheets with all items that are new since the last time the data portals were harvested                                
newItemsReport = directory + "\\reports\\allNewItems_%s.csv" % (ActionDate)
printNewItemReport(newItemsReport, fieldnames, All_New_Items)

### prints a csv spreadsheets with all items that are deleted since the last time the data portals were harvested  
delItemsReport = directory + "\\reports\\allDeletedItems_%s.csv" % (ActionDate)
printDeletedItemReport(delItemsReport, delFieldsReport, All_Deleted_Items)       
    
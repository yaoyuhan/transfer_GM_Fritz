#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 09:50:07 2020

@author: yuhanyao
"""

import os
import json
import requests
import pickle
import numpy as np
import pandas as pd
from copy import deepcopy
from astropy.table import Table
from astropy.time import Time
import astropy.io.ascii as asci
from astropy import units as u
from astropy.coordinates import SkyCoord

global GETTOKEN, BASEURL, GETTOKEN2

f = open("files/fritz_token_classify") # the ACLS of this token needs to be 'Classify'
GETTOKEN = f.readline().split("\n")[0]
f.close()


f = open("files/fritz_token_upload") # the ACLS of this token needs to be 'Upload'
GETTOKEN2 = f.readline().split("\n")[0]
f.close()

BASEURL = 'https://fritz.science/'


def api(method, endpoint, data=None):
    ''' 
    Info : Basic API query, takes input the method (eg. GET, POST, etc.), the endpoint (i.e. API url) 
               and additional data for filtering
    Returns : response in json format
    '''
    headers = {'Authorization': f'token {GETTOKEN}'}
    response = requests.request(method, endpoint, json=data, headers=headers)
    #if(response.json()['status'] == 'success'):
    #    pass
    #else:
    #    print('ERROR, Query failed!')
    return response.json()


def api_upload(method, endpoint, data=None):
    ''' 
    Info : Basic API query, takes input the method (eg. GET, POST, etc.), the endpoint (i.e. API url) 
               and additional data for filtering
    Returns : response in json format
    '''
    headers = {'Authorization': f'token {GETTOKEN2}'}
    response = requests.request(method, endpoint, json=data, headers=headers)
    #if(response.json()['status'] == 'success'):
    #    pass
    #else:
    #    print('ERROR, Query failed!')
    return response.json()


def get_source_api(ztfname):
    ''' 
    Info : Query a single source, takes input ZTF name
    Returns : all basic data of that source (excludes photometry and spectra, 
                includes redshift, classification, comments, etc.)
    '''
    url = BASEURL+'api/sources/'+ztfname
    response = api('GET',url)
    return response['data']    

def get_group_ids(groupnames=['Nuclear Transients']):
    ''' 
    Info : Query group ids of groups
    Returns : List of group ids 
    '''
    url = BASEURL+'api/groups'
    headers = {'Authorization': f'token {GETTOKEN}'}
    groupnames = np.atleast_1d(groupnames)
    grpids = []
    for grpname in groupnames:
        response = requests.request('GET',url,params={'name':grpname}, headers=headers).json()
        grpids.append(response['data'][0]['id'])
    return grpids


def save_alert_to_group(ztfname, groupname):
    ''' 
    Info : Save an alert to given group(s), takes the ZTF name and list of group names
    Returns : response with status
    '''
    url = BASEURL+'api/alerts/ztf/'+ztfname
    filt = {'group_ids':get_group_ids(groupname)}
    headers = {'Authorization': f'token {GETTOKEN}'}
    response = requests.request('POST', url, json=filt, headers=headers)
    return response.json()


def post_classification(ztfname, classification, probability=1.0):
    '''
    Info : Post a classification, takes input ZTF name, classification and taxonomy_id 
           (1 for sitewide, 2 for basic). Only classifications within that taxonomy are permitted.
            Check Fritz API query to list all taxonomies in documentation
    '''
    url = BASEURL+'api/classification'
    filt = {"obj_id":ztfname,
            'classification':classification,
            'taxonomy_id':1,
            "probability":probability
            #'group_ids':get_group_ids() #default to all of requesting user's groups.
           }
    print(filt)
    response = api('POST',url,filt)
    return response


def post_redshift(ztfname, redshift):
    """
    Post a redshift
    """
    url = BASEURL+'api/sources/%s'%ztfname
    filt = {"redshift":redshift
            #'group_ids':get_group_ids() #default to all of requesting user's groups.
           }
    print(filt)
    response = api_upload('PATCH',url,filt)
    return response
    
    

def bulk_transfer_jsonfile(jsonfile = "json_dumps/ZTFBH_Nuclear_2020-11-25.json"):
    f=open(jsonfile)
    data = json.load(f)
    f.close()
    
    ndata = len(data)
    
    cs = []
    for i in range(len(data)):
        dt = data[i]
        if dt["classification"] not in cs:
            cs.append(dt["classification"])
        #if dt["classification"]=="Off-nuclear AGN":
        #    print (dt["name"])
    
    for i in range(3404, len(data)):
        dt = data[i]
        name = dt["name"]
        classification = dt["classification"]
        redshift = dt["redshift"]
        if classification == "TDE":
            classification = "Tidal Disruption Event"
            probability = 1.0
        elif classification == "TDE?":
            classification = "Tidal Disruption Event"
            probability = 0.5
        elif classification in ["AGN", "CLAGN", "Off-nuclear AGN", 'AGN ']:
            classification = "AGN"
            probability = 1.0
        elif classification in ["AGN?", "AGN? ", 'CLAGN?']:
            classification = "AGN"
            probability = 0.5
        elif classification == "NLS1":
            classification = "Seyfert"
            probability = 1.0
        elif classification == "NLS1?":
            classification = "Seyfert"
            probability = 0.5
        elif classification in ["blazar", "Blazar"]:
            classification = "Blazar"
            probability = 1.0
        elif classification == "blazar?":
            classification = "Blazar"
            probability = 0.5
        elif classification in ["QSO", 'quasar']:
            classification = "QSO"
            probability = 1.0
        elif classification == "QSO?":
            classification = "QSO"
            probability = 0.5
        elif classification == "LINER": # Low-ionization nuclear emission-line region
            classification = "Galactic Nuclei"
            probability = 1.0
        else:
            continue # I don't care about other classifications
        
        info = get_source_api(name)
        
        print ("%d/%d"%(i, ndata))
        #### the source had never been saved before
        if info == {}:
            if classification == "Tidal Disruption Event":
                groupname = "Tidal Disruption Events"
            else:
                groupname = "Nuclear Transients"
            print ("Saving %s to %s"%(name, groupname))
            save_alert_to_group(name, groupname)
            print ("Classify %s as %s"%(name, classification))
            post_classification(name, classification, probability)
        #### the source had been saved before
        else:
            #### no classification had been assigned
            if info["classifications"]==[]:
                print ("Classify %s as %s"%(name, classification))
                post_classification(name, classification, probability)
            else:
                #### classification is already correctly assigned
                if info["classifications"][0]["classification"] == classification:
                    print ("classification is correct")
                #### assigned classification is not very good
                else:
                    print ("Classify %s as %s"%(name, classification))
                    post_classification(name, classification, probability)
                    
        if classification == "Tidal Disruption Event":
            if redshift is not None:
                post_redshift(name, redshift)
        
        
#bulk_transfer_jsonfile(jsonfile = "json_dumps/ZTFBH_Nuclear_2020-11-23.json")
#bulk_transfer_jsonfile(jsonfile = "json_dumps/ZUDS_2020-11-09.json")    
#bulk_transfer_jsonfile(jsonfile = "json_dumps/ZTFBH_Offnuclear_2020-11-09.json")
bulk_transfer_jsonfile(jsonfile = "json_dumps/Redshift_Completeness_Factor_2020-11-09.json")
    
    
    
    
    
    
    

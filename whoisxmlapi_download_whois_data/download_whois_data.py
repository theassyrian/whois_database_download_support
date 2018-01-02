#!/usr/bin/env python2
#
#Script to download data from WhoisXML API subscriptions
#Provided for subscribers of quarterly whois data feeds
#
#Copyright (c) 2010-2017 Whois API LLC,  http://www.whoisxmlapi.com
#

import sys
import os

import argparse
from argparse import RawTextHelpFormatter

import easygui as g

import re

import gzip
import datetime

import whois_utils.WhoisDataFeed as wdf
import whois_utils.whois_user_interaction as whois_user_interaction

from whois_utils.whois_user_interaction import *

#GlobalSettings
VERSION = "0.0.3"
MYNAME = sys.argv[0].replace('./','')
FEEDCONFIGDIR='.'

#Read the list of supported formats. Probably the directory with "feeds.ini" should be given more precisely.
formatmatrix = wdf.feed_format_matrix(FEEDCONFIGDIR)
feed_descriptions = wdf.feed_descriptions(FEEDCONFIGDIR)

if len(sys.argv) > 1 and sys.argv[-1].strip() != '--interactive':
    DIALOG_COMMUNICATION = False
    
    #command-line version, load_mysql_data.pyw has been started
    #Here we parse the command-line and get the values of the arguments
    parser = argparse.ArgumentParser(description='Python script to download data from WhoisXML API feeds\n\nA script for data feed subscribers of WhoisXML API\nSee usage examles in the supplied README file.', prog=MYNAME, formatter_class=RawTextHelpFormatter)
    #Vebosity, version, etc.
    parser.add_argument('--version',
                            help = 'Print version information and exit.',
                        action = 'version', version = MYNAME + ' ver. ' + VERSION +'\n(c) WhoisXML API LLC.')
    parser.add_argument('-v', '--verbose', help='Print messages. Recommended. \nIf not specifies, the script runs quietly,\nonly errors are reported.', action='store_true')
    parser.add_argument('-d', '--debug', help='Debug mode, even more messages', action='store_true')
    parser.add_argument('--maxtries', help='Maximum number of tries when downloading. Defaults to 5.')
    parser.add_argument('--interactive', help='Interactive mode. \nIf proivded as a first argument, \nyou will be prompted for the parameters in GUI dialogue windows.')
    parser.add_argument('--username', help='Username for the feed.')
    parser.add_argument('--password', help='Password for the feed.')
    parser.add_argument('--list-feeds', help='List supported feeds. Other arguments are ignored', action='store_true')
    parser.add_argument('--feed', help='Use this feed')
    parser.add_argument('--list-dataformats', help='List the data formats supported by the feed', action='store_true')
    parser.add_argument('--dataformats', help='The data formats to be downloaded.')
    parser.add_argument('--db-version', help= 'The quarterly db version to load.\nRequired for daily feeds Format: vNN, e.g. v19')
    parser.add_argument('--startdate', help= 'The starting date for quarterly feed download, format: YYYYMMDD')
    parser.add_argument('--enddate', help= 'The end date for quarterly feed download, format: YYYYMMDD.\nIf not provided, data are loaded for the startdate only.')
    parser.add_argument('--list-supported-tlds', help='download data for these tlds.', action='store_true')
    parser.add_argument('--tlds', help='Download data for these tlds. For data formats which are tld independent, you must chose a single supported by the feed, but it will be ignored.')
    parser.add_argument('--output-dir', help='Directory to download files into.')
    args = parser.parse_args()
    args = vars(args)
    whois_user_interaction.VERBOSE = args['verbose']
    whois_user_interaction.DEBUG = args['debug']
    whois_user_interaction.DIALOG_COMMUNICATION = False
    #The user wants to list feeds
    if args['list_feeds']:
        print "\nSupported feeds and data formats: "
        sys.stderr.write("\n")
        for feed in formatmatrix.keys():
            sys.stderr.write("Feed: %.60s \n      formats: " % feed)
            for f in formatmatrix[feed]:
                sys.stderr.write("%s " % f)
            sys.stderr.write("\n")
        sys.stderr.write("\n\n")
        exit(6)
    #Check if feed is specified and valid
    if args['feed'] == None:
        print_error_and_exit('You must specify a feed. See --list_feeds for the list of supported feeds and their data formats.')
    if args['feed'] not in set(formatmatrix.keys()):
        print_error_and_exit('Invalid feed. See --list_feeds for the list of supported feeds and their data formats.')        
    #The user wants data formats for this feed
    if args['list_dataformats']:
        print "Data formats for feed %s: " % args['feed']
        for f in formatmatrix[args['feed']]:
            sys.stderr.write("%s " % f)
        sys.stderr.write("\n")
        exit(6)
    #Collect and vaidate data formats
    try:
        args['dataformats'] = args['dataformats'].split(',')
    except:
        print_error_and_exit('No data formats specified')
        
    for f in args['dataformats']:
        if f not in set(formatmatrix[args['feed']]):
            print_error_and_exit('Feed %s does not support the data format %s.' % (args['feed'], f))
    #Create feeds
    feeds=[]
    for dataformat in args['dataformats']:
        the_feed = wdf.WhoisDataFeed()
        the_feed.set_maxtries(args['maxtries'])
        the_feed.set_feed_type(FEEDCONFIGDIR, args['feed'], dataformat)
        feeds.append(the_feed)
    #Set database version for quarterly feeds
    if the_feed.is_quarterly:
        if re.match(r'^v[0-9]+$', str(args['db_version'])) != None:
            for f in feeds:
                f.set_quarterly_dbversion(args['db_version'])
        else:
            print_error_and_exit('Database version not specified for quarterly feed, or invalid format. Should be e.g. "v20".')
    #Set intervals for daily feeds
    elif the_feed.is_daily:
        if args['startdate'] == None or not re.match(r'^[0-9]{8}$', str(args['startdate'])):
            print_error_and_exit('Start date must be specified for a daily feed, in the format YYYYMMDD')
        startdate = datetime.datetime.strptime(args['startdate'],'%Y%m%d')
        if args['enddate'] != None:
            if re.match(r'^[0-9]{8}$', str(args['enddate'])):
                enddate = datetime.datetime.strptime(args['enddate'],'%Y%m%d')
                if enddate < startdate:
                    print_error_and_exit('End date must be later than start date.')
            else:
                print_error_and_exit('End date must be in the format, in the format YYYYMMDD')
        else:
            enddate = None
        #set up the date intervals of the feeds
        for f in feeds:
            f.set_daily_feed_interval(startdate, enddate)
    #setup login credentials
    for the_feed in feeds:
        if args['username'] != None and args['password'] != None:
            the_feed.set_login_credentials(args['username'], args['password'])
        else:
            the_feed.set_login_credentials('', '')
    the_feed.test_http_access()
    if not the_feed.loginOK:
        print_error_and_exit('Login failed. Probably bad username or password specified in the command-line or in ~/.whoisxmlapi_login.ini')
        #Update list of available tlds
    for the_feed in feeds:
        the_feed.open_http_session()
        the_feed.update_supported_tlds()
    available_tlds = [set(the_feed.supported_tlds) for the_feed in feeds]
    available_tlds = sorted(list(frozenset().union(*available_tlds)))
    if args['list_supported_tlds']:
        sys.stderr.write("Available tlds:\n")
        for tld in available_tlds:
            sys.stderr.write('%s, ' % tld)
        sys.stderr.write("\n")
        exit(6)
    #Verify supported tlds list
    try:
        args['tlds'] = args['tlds'].split(',')
    except:
        print_error_and_exit('You must specifiy the list of tlds to download')
    tldsset=set(args['tlds'])
    args['tlds'] = list(tldsset.intersection(set(available_tlds)))
    if args['tlds'] == []:
        print_error_and_exit('All specified tlds are unsupported.')
    #verify if the output directory exists
    if args['output_dir'] == None:
        print_error_and_exit('Please specify the output directory.')
    args['output_dir'] = os.path.abspath(args['output_dir'])
    if not(os.path.isdir(args['output_dir'])):
        print_error_and_exit('The output directory %s does not exist' % args['output_dir'])
    #Now we have set up everything to do some downloading
else:
    #Interacitve version with easygui
    args = {}
    DIALOG_COMMUNICATION = True
    whois_user_interaction.VERBOSE = True
    whois_user_interaction.DEBUG = False
    whois_user_interaction.DIALOG_COMMUNICATION = True
    #Things you cannot do when interactive
    #Note: set the next two to True for console debug
    args['verbose'] = True
    args['debug'] = False
    #Default window title
    windowtitle='WhoisXML API MySQL data downloader script'
    
    answer = g.msgbox('This is %s: a script to download data feeds from WhoisXML API subscriptions.\n(C) WhoisXML API LLC.\n\nPlease make sure that you have the username and password \n\nPress O.K. to start.' % (MYNAME), windowtitle)
    if answer == None:
        exit(6)
    feeds = formatmatrix.keys()
    #a not very elegant solution to overcome limitations of easygui
    feedoptions=[]
    feedorder=[]
    for feed in sorted(feeds):
        feedoptions.append(feed.ljust(42)+": "+feed_descriptions[feed])
        feedorder.append(feed)
    answer = g.choicebox("Choose a feed you would like to download data from.\nNote: you have to be a subscriber of that.", windowtitle, feedoptions)
    if answer == None:
        exit(6)
    feedno = feedoptions.index(answer)
    args['feed'] = feedorder[feedno]
    answer = g.multchoicebox("Choose the preferred data format(s)", windowtitle, formatmatrix[args['feed']])
    if answer == None:
        exit(6)
    args['dataformats'] = answer

    #Start initializing feed
    feeds=[]
    for dataformat in args['dataformats']:
        the_feed=wdf.WhoisDataFeed()
        the_feed.set_feed_type(FEEDCONFIGDIR, args['feed'], dataformat)
        feeds.append(the_feed)
    #If a quarterly feed is chosen, we must get the dbversion
    if the_feed.is_quarterly:
        while the_feed.dbversion == None:
            answer = g.enterbox("You have chosen a quarterly feed. Please suppy the database version, e.g. 'v20'", windowtitle)
            if re.match(r'^v[0-9]+$', answer) != None:
                the_feed.set_quarterly_dbversion(answer)
                args['db_version'] = answer
            else:
                answer = g.ynbox('Invalid feed name format. Try again?')
                if not answer:
                    exit(1)
        args['db-version']=answer
        for f in feeds:
            f.set_quarterly_dbversion(answer)
    elif the_feed.is_daily:
        startdate = None
        while startdate == None:
            answer = g.enterbox("You have chosen a daily feed. Please specify the first day to download data for \nin the form 'YYYYMMDD', e.g. '20170728'", windowtitle)
            if answer == None:
                exit(6)
            if not re.match(r'^[0-9]{8}$', answer):
                startdate = None
            else:
                startdate = answer
                args['startdate'] = answer
        startdate = datetime.datetime.strptime(startdate,'%Y%m%d')
        enddate = None
        while enddate == None:
            answer = g.enterbox("Please suppy the last day you are interested in \n in the format 'YYYYMMDD', e.g. '20170728'\nLeve blank and press O.K. if you want do download a single day only.", windowtitle)
            if answer == None:
                exit(6)
            if not (re.match(r'^[0-9]{8}$', answer) or answer == ''):
                args['enddate'] = answer
                enddate = None
            else:
                args['startdate'] = answer
                enddate = answer
        if enddate == '':
            enddate = None
        else:
            enddate = datetime.datetime.strptime(enddate,'%Y%m%d')
        print_verbose('Start date: %s\nEnd date: %s' % (str(startdate), str(enddate)))
        for f in feeds:
            f.set_daily_feed_interval(startdate, enddate)
                
    #Get and verify user acces credentials for the feed
    defaultusername=''
    while not the_feed.loginOK:
        answer = g.enterbox('Enter your username for the chosen WhoisXML API feed.\nLeave it empty if you have configured ~/.whoisxmlapi_login.ini', windowtitle,default = defaultusername)
        if answer == None:
            exit(6)
        args['username'] = answer
        defaultusername = answer
        if answer.strip() != '':
            answer = g.passwordbox('Enter your password for the user %s' % (args['username'],), windowtitle)
            if answer == None:
                exit(6)
        #If the username is an empty string, the password will be also one.
        args['password'] = answer
        the_feed.set_login_credentials(args['username'], args['password'])
        the_feed.test_http_access()
        if not the_feed.loginOK:
            answer = g.ynbox('Login failed. Bad login/password, or nonexistent database version. \nIf read from ~/.whoisxmlapi_login.ini, then it is probably wrong there.\n(To re-enter database version, quit now and start again.\nTry to enter username and password again?')
            if not answer:
                exit(1)
    for the_feed in feeds:
        the_feed.set_login_credentials(args['username'], args['password'])

    #Feed has been set up now.
    #For daily feeds, get date range
    
    #Update list of available tlds
    for the_feed in feeds:
        the_feed.open_http_session()
        the_feed.update_supported_tlds()
    available_tlds = [set(the_feed.supported_tlds) for the_feed in feeds]
    available_tlds = sorted(frozenset().union(*available_tlds))
    answer = g.multchoicebox("Choose the TLDs for which you want to load data.\n Note: For formats independent of tlds, your choice will be ignored, but you have to choose one.", windowtitle, available_tlds)
    if answer == None:
        exit(6)
    args['tlds']=answer
    print_verbose('Tlds to load: %s' % (str(args['tlds']),))

    #Choose the output root directory
    answer = g.diropenbox(title=windowtitle, msg='Choose the directory to download files into.')
    if answer == None:
        exit(6)
    args['output_dir'] = answer

print_verbose('Feed to download from: %s' % (args['feed'],))
print_verbose('Data format(s): %s' % (str(args['dataformats']),))

if feeds[0].is_quarterly:
    print_verbose('Quarterly feed database version: %s' % (args['db_version'],))
if feeds[0].is_daily:
    print_verbose('Daily feed start date: %s\nend date: %s' % (str(startdate), str(enddate)))

print_verbose('Tlds(s) (only the supported ones): %s' % (str(args['tlds']),))

#The main job will start here
total_failed = []
for f in feeds:
    f.download_feed_into_directory(args['tlds'], args['output_dir'])
    total_failed += f.failed
#removing duplicates as some feeds might download redundantly
total_failed=list(set(total_failed))
print_verbose('Download finished.')
if len(total_failed) > 0:
    print_verbose('The following URLs have failed (probably they do not exist)')
    for u in total_failed:
        print_verbose(u)
    print_verbose('Re-run with the same settings to retry')
else:
    print_verbose('Everything has been downloaded successfully.')
        
if DIALOG_COMMUNICATION:
    _ = g.msgbox("%s has finished its activity.\nPlease take a look at the terminal window to see the log.\nAfterwards, press OK to close this window and quit." %(MYNAME), windowtitle)
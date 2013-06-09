#!/usr/bin/python
#TheRoyalWe
#

############################
### Imports		 ###
############################	

import urllib2, urllib, sys, os, re, random, copy, shutil
import xbmc,xbmcplugin,xbmcgui,xbmcaddon
import HTMLParser
from urllib import quote_plus
#from t0mm0.common.net import Net
from t0mm0.common.addon import Addon
from metahandler import metahandlers
#net = Net()

ADDON_ID = 'plugin.video.theroyalwe'
ADDON_NAME = 'The Royal We'
ADDON = xbmcaddon.Addon(id=ADDON_ID)
selfAddon = ADDON
addon = Addon(ADDON_ID)
rootpath = selfAddon.getAddonInfo('path')
VERSION = selfAddon.getAddonInfo('version')
#sys.path.append( os.path.join( rootpath, 'resources', 'lib' ) )
art = rootpath+'/resources/artwork'
#art = 'http://dudehere-repository.googlecode.com/git/artwork'
from BeautifulSoup import BeautifulSoup, Tag, NavigableString
from donnie import scrapers



############################
### Enviornment		 ###
############################


datapath = addon.get_profile()
cookie_path = os.path.join(xbmc.translatePath(datapath + 'cookies'), '')
if not os.path.exists(cookie_path):
	os.makedirs(cookie_path)
cookie_jar = os.path.join(cookie_path, "cookiejar.lwp")
USER_AGENT = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
DATA_PATH = os.path.join(xbmc.translatePath('special://profile/addon_data/' + ADDON_ID), '')
SITE_REFERRER = 'xbmc.org'
STREAM_SELECTION = ''

############################
### Settings		 ###
############################

def str2bool(v):
	return v.lower() in ("yes", "true", "t", "1")

from donnie.settings import Settings
reg = Settings(['plugin.video.theroyalwe', 'script.module.donnie'])


LOGGING_LEVEL = reg.getSetting('logging-level')

if reg.getBoolSetting('movie_custom_directory'):
	MOVIES_PATH = reg.getSetting('movie_directory')
else:
	MOVIES_PATH = os.path.join(xbmc.translatePath(DATA_PATH + 'movies'), '')

if reg.getBoolSetting('tv_show_custom_directory'):
	TV_SHOWS_PATH = reg.getSetting('tv_show_directory')
else:
	TV_SHOWS_PATH = os.path.join(xbmc.translatePath(DATA_PATH + 'tvshows'), '')

USE_META = reg.getBoolSetting('enable-metadata')



MOVIES_DATA_PATH = os.path.join(xbmc.translatePath(DATA_PATH + 'movies_data'), '')
TV_SHOWS_DATA_PATH = os.path.join(xbmc.translatePath(DATA_PATH + 'tvshows_data'), '')
DOWNLOAD_PATH = os.path.join(xbmc.translatePath(DATA_PATH + 'download'), '')
RECENTLY_AIRED_PATH = os.path.join(xbmc.translatePath('special://profile'), 'playlists/video/RecentlyAired.xsp')
EXCLUDE_PROBLEM_EPISODES = True
AZ_DIRECTORIES = ['#1234', 'A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y', 'Z']



############################
### Database		 ###
############################

from donnie.databaseconnector import DataConnector

Connector = DataConnector()
if Connector.getSetting('database_mysql')=='true':
	DB_TYPE = 'mysql'
else:
	DB_TYPE = 'sqlite'
DB = Connector.GetConnector()
VDB = Connector.GetVDBConnector()


def BackupDatabase():
	from datetime import datetime
	path = os.path.join(xbmc.translatePath(DATA_PATH + 'backup'), '')
	CreateDirectory(path)
	ts = str(datetime.now())
	ts = ts.replace(':', '.')
	filename = 'theroyalwe.%s' % ts
	backupfile = xbmcpath(path, filename)
	dialog = xbmcgui.Dialog()
	msg = 'Database Backup!'
	msg2 = "Great idea, though this may take a few minuts."
	msg3 = "Do you want to continue?"
	if not dialog.yesno(msg, msg2, msg3): return

	pDialog = xbmcgui.DialogProgress()
	pDialog.create('Creating Backup File')
	DB.connect()
	if DB.createBackupFile(backupfile, ts, pDialog):
		Notify('Backup Complete!', backupfile+'.bkf')
	pDialog.close()

def RestoreDatabase():
	DB.connect()
	dialog = xbmcgui.Dialog()
	path = os.path.join(xbmc.translatePath(DATA_PATH + 'backup'), '')
	CreateDirectory(path)
	msg = 'Database Restore!'
	msg2 = "************* WARNING *************"
	msg3 = "This is dangerous, do you want to continue?"
	if not dialog.yesno(msg, msg2, msg3): return
	fileBrowser = xbmcgui.Dialog()
	backupfile = fileBrowser.browse(1, 'Select a backup file', 'files', '.bkf', False, False, path)
	msg = 'Database Restore!'
	msg2 = "************* WARNING *************"
	msg3 = "Last chance, do you really want to continue?"
	if not dialog.yesno(msg, msg2, msg3): return
	pDialog = xbmcgui.DialogProgress()
	pDialog.create('Restoring From Backup File')
	if DB.restoreBackupFile(backupfile, pDialog):
		Notify('Restore Complete!', '')
	pDialog.close()

###########################
### General functions 	###
###########################

def checkUpgradeStatus():
	log('Verifying Upgrade Status')
	status = reg.getSetting('upgrade-status')
	if status < VERSION:
		dialog = xbmcgui.Dialog()
		dialog.ok('TRW Version Update!', 'Make sure the database settings are correct.')
		xbmcaddon.Addon(id='script.module.donnie').openSettings()
		
		msg = 'TRW needs to update your database!'
		msg2 = "This will take some time depending depending on the size."
		msg3 = "Do you wish to backup first?"
		if dialog.yesno(msg, msg2, msg3):
			BackupDatabase()
		
		if not dialog.yesno('Ready to proceed?', "It's not too late to cancel."): 
			sys_exit()
			return
		ExecuteUpgrade()

def ExecuteUpgrade():
	DB.connect()
	dialog = xbmcgui.Dialog()
	pDialog = xbmcgui.DialogProgress()
	pDialog.create('Upgrading Database')
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	if DB_TYPE == 'mysql':
		rows = DB.query("SELECT rw_shows.showid, rw_shows.imdb, rw_shows.showname FROM rw_subscriptions JOIN rw_shows ON rw_subscriptions.showid=rw_shows.showid WHERE isNull(rw_shows.imdb) OR rw_shows.imdb='0'", force_double_array=True)
	else:
		rows = DB.query("SELECT rw_shows.showid, rw_shows.imdb, rw_shows.showname FROM rw_subscriptions JOIN rw_shows ON rw_subscriptions.showid=rw_shows.showid WHERE rw_shows.imdb IS NULL OR rw_shows.imdb='0'", force_double_array=True)

	for row in rows:
		if (pDialog.iscanceled()):
			sys_exit()
			return
		percent =  ( rows.index(row) * 100 / len(rows) )
		status = "%s of %s" % (rows.index(row), len(rows))
		pDialog.update(percent, status, '')
		imdb = SCR.resolveIMDB(showid=row[0])

	msg = 'Upgrade Complete!'
	msg2 = "For questions, support or feeback go to:"
	msg3 = "[B]http://xbmchub.com/forum/[/B]"
	dialog.ok(msg, msg2, msg3)
	ADDON.setSetting('upgrade-status', str(VERSION))
	
	
def sys_exit():
	exit = xbmc.executebuiltin("XBMC.ActivateWindow(Home)")
	return exit
def Notify(title, message, image=''):
	if image == '':
		image = xbmcpath(rootpath, 'icon.png')
	xbmc.executebuiltin("XBMC.Notification("+title+","+message+", 1000, "+image+")")

def xbmcpath(path,filename):
     translatedpath = os.path.join(xbmc.translatePath( path ), ''+filename+'')
     return translatedpath

def showQuote():
	filepath = xbmcpath(rootpath+'/resources/', 'quotes.txt')
	f = open(filepath)
	lines = f.readlines(100)
	n= random.randint(0, len(lines)-1)
	quote = lines[n]
	Notify('', quote)


def htmldecode(body):
	h = HTMLParser.HTMLParser()
	body = h.unescape(body)
	try:
	    encoding = req.headers['content-type'].split('charset=')[-1]
	except:
	    enc_regex = re.search('<meta.+?charset=(.+?)" />')
	    encoding = enc_regex.group(1)
	body = unicode(body, encoding).encode('utf-8')
	return body

def log(msg, v=None, level=1):
	if v:
		msg = msg % v

	if (LOGGING_LEVEL == '1' or level == 0):
		print msg

def ClearDatabaseLock():
	dialog = xbmcgui.Dialog()
	if dialog.yesno("Clear Database Lock?", "If a job has failed, you may manually delete the database lock.", "Do you want to proceed?"):
		DB.connect()
		DB.execute("UPDATE rw_status SET updating=0, job=''")
		DB.commit()


class TextBox:
	# constants
	WINDOW = 10147
	CONTROL_LABEL = 1
	CONTROL_TEXTBOX = 5

	def __init__( self, *args, **kwargs):
		# activate the text viewer window
		xbmc.executebuiltin( "ActivateWindow(%d)" % ( self.WINDOW, ) )
		# get window
		self.window = xbmcgui.Window( self.WINDOW )
		# give window time to initialize
		xbmc.sleep( 100 )


	def setControls( self ):
		#get header, text
		heading, text = self.message
		# set heading
		self.window.getControl( self.CONTROL_LABEL ).setLabel( "%s - %s" % ( heading, ADDON_NAME, ) )
		# set text
		self.window.getControl( self.CONTROL_TEXTBOX ).setText( text )

   	def show(self, heading, text):
		# set controls

		self.message = heading, text
		self.setControls()



def RemoveDirectory(dir):
	dialog = xbmcgui.Dialog()
	if dialog.yesno("Remove directory", "Do you want to remove directory?", dir):
		if os.path.exists(dir):
			pDialog = xbmcgui.DialogProgress()
			pDialog.create(' Removing directory...')
			pDialog.update(0, dir)	
			shutil.rmtree(dir)
			pDialog.close()
			Notification("Directory removed", dir)
		else:
			Notification("Directory not found", "Can't delete what does not exist.")	
	

	

def CreateDirectory(dir_path):
	dir_path = dir_path.strip()
	if not os.path.exists(dir_path):
		os.makedirs(dir_path)
			
def readfile(path, soup=False):
	try:
		file = open(path, 'r')
		content=file.read()
		file.close()
		if soup:
			soup = BeautifulSoup(content)
			return soup
		else:
			return content
	except:
		return ''

def writefile(path, content):
	try:
		file = open(path, 'w')
		file.write(content)
		file.close()
		return True
	except:
		return False

def DoSearch(msg):
	kb = xbmc.Keyboard('', msg, False)
    	kb.doModal()
	if (kb.isConfirmed()):
        	search = kb.getText()
        	if search != '':
			return search
		else:
			return False


def SetupLibrary():
	log("Trying to add Library source paths...")
	source_path = os.path.join(xbmc.translatePath('special://profile/'), 'sources.xml')
	
	try:
		file = open(source_path, 'r')
		content=file.read()
		file.close()
		soup = BeautifulSoup(content)
	except:
		soup = BeautifulSoup()
		sources_tag = Tag(soup, "sources")
		soup.insert(0, sources_tag)
		
	if soup.find("video") == None:
		sources = soup.find("sources")
		video_tag = Tag(soup, "video")
		sources.insert(0, video_tag)
		
	video = soup.find("video")

	CreateDirectory(MOVIES_PATH)
	if len(soup.findAll(text="Movies (The Royal We)")) < 1:
		movie_source_tag = Tag(soup, "source")
		movie_name_tag = Tag(soup, "name")
		movie_name_tag.insert(0, "Movies (The Royal We)")
		MOVIES_PATH_tag = Tag(soup, "path")
		MOVIES_PATH_tag['pathversion'] = 1
		MOVIES_PATH_tag.insert(0, MOVIES_PATH)
		movie_source_tag.insert(0, movie_name_tag)
		movie_source_tag.insert(1, MOVIES_PATH_tag)
		video.insert(2, movie_source_tag)

	CreateDirectory(TV_SHOWS_PATH)
	if len(soup.findAll(text="TV Shows (The Royal We)")) < 1:	
		tvshow_source_tag = Tag(soup, "source")
		tvshow_name_tag = Tag(soup, "name")
		tvshow_name_tag.insert(0, "TV Shows (The Royal We)")
		tvshow_path_tag = Tag(soup, "path")
		tvshow_path_tag['pathversion'] = 1
		tvshow_path_tag.insert(0, TV_SHOWS_PATH)
		tvshow_source_tag.insert(0, tvshow_name_tag)
		tvshow_source_tag.insert(1, tvshow_path_tag)
		video.insert(2, tvshow_source_tag)
	pDialog = xbmcgui.DialogProgress()
	log(soup.prettify())
	string = ""
	for i in soup:
		string = string + str(i)
	
	file = open(source_path, 'w')
	file.write(str(soup))
	file.close()
	log("Source paths added!")
	
	dialog = xbmcgui.Dialog()
	dialog.ok("Source folders added", "To complete the setup:", " 1) Restart XBMC.", " 2) Set the content type of added folders.")	




def WaitIf():
	#killing playback is necessary if switching playing of stream to another
	if xbmc.Player().isPlayingVideo() == True:
		xbmc.Player().stop()

###########################
### Streaming		###
###########################


def LaunchStream(path, episodeid=None, movieid=None, ignore_prefered = False):
	if path == getLastPath():
		ignore_prefered = True
	_path = path	
	_episodeid = episodeid
	_movieid = movieid
	log("Launching strm: %s" % path)
	log("Getting links by Service")

	DB.connect()
	DB.execute("DELETE FROM rw_stream_list WHERE machineid=?", [reg.getSetting('machine-id')])
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	SCR.getStreams(episodeid=episodeid, movieid=movieid)

	if reg.getBoolSetting('enable-autorank'):
		service_streams = DB.query("SELECT stream, url from rw_stream_list WHERE machineid=? ORDER BY priority ASC", [reg.getSetting('machine-id')], force_double_array=True)
	else:
		service_streams = DB.query("SELECT stream, url from rw_stream_list WHERE machineid=?", [reg.getSetting('machine-id')], force_double_array=True)
	if len(service_streams) == 0:
		Notify('Streaming Error!', 'Could not find any viable links')
		return False
	if not ignore_prefered and reg.getBoolSetting('enable-autoplay') and reg.getBoolSetting('enable-autorank'):

		for attempt in range(1,4):
			log('Trying prefered host attempt: %s', attempt)
			try:
				row =  DB.query("SELECT url from rw_stream_list WHERE machineid=? ORDER BY priority ASC LIMIT ?,1",[attempt,reg.getSetting('machine-id')])
				host = row[0]
				resolved_url = SCR.resolveStream(host)
				break
			except:
				resolved_url = None
				pass
		if not resolved_url:
			log("Failed resolving prefered host, will ask for another mirror")
			Notify('Streaming Error!', 'Autoplay failed, select a different Stream')
			resolved_url = ShowStreamSelect(SCR, service_streams)
	else:
		log("Asking for a mirror")
		resolved_url = ShowStreamSelect(SCR, service_streams)

	if episodeid:
		if DB_TYPE == 'mysql':
			SQL = "SELECT CONCAT(rw_shows.showname, ' ', rw_episodes.season, 'x', rw_episodes.episode, ' ',  rw_episodes.name) AS name FROM rw_episodes JOIN rw_shows ON rw_episodes.showid=rw_shows.showid WHERE episodeid=? LIMIT 1"
		else:
			SQL = "SELECT rw_shows.showname || ' ' || rw_episodes.season || 'x' || rw_episodes.episode || ' ' ||  rw_episodes.name AS name FROM rw_episodes JOIN rw_shows ON rw_episodes.showid=rw_shows.showid WHERE episodeid=? LIMIT 1"
		row = DB.query(SQL, [episodeid])
		name = row[0]
		media='tvshow'
	if movieid:
		row = DB.query("SELECT rw_movies.movie FROM rw_movies WHERE imdb=? LIMIT 1", [movieid])
		name = row[0]
		media='movie'
	try:
		VDB.videoLibraryConnect()
		idFile = VDB.setWatchedFlag(path)
	except: 
		idFile = None

	setLastPath(_path)
	try:	
		StreamSource(name,resolved_url, media=media, idFile=idFile)
	except:
		Notify('Streaming Error!', 'Selected mirror bailed, try a different Stream')
		log("Failed launching stream")
		

def getLastPath():
	return ADDON.getSetting('last-path')

def setLastPath(path):
	ADDON.setSetting('last-path', path)

def WatchStream(name, action, ignore_prefered = False):
	if name == getLastPath():
		ignore_prefered = True
	_name = name
	log("Gettings Streams: %s, %s" % (name, action))
	DB.connect()
	DB.execute("DELETE FROM rw_stream_list WHERE machineid=?", [reg.getSetting('machine-id')])
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	total = len(SCR.activeScrapers)

	if action=='movie':	
		rows = DB.query("SELECT movieid FROM rw_movies WHERE movie=?", [name], force_double_array=True)
		for row in rows:
			index = rows.index(row)
			imdb = SCR.resolveIMDB(movieid=row[0])
		SCR.getStreams(movieid=imdb)
	else:
		SCR.getStreams(episodeid=name)

	if reg.getBoolSetting('enable-autorank'):
		service_streams = DB.query("SELECT stream, url from rw_stream_list WHERE machineid=? ORDER BY priority ASC", [reg.getSetting('machine-id')], force_double_array=True)
	else:
		service_streams = DB.query("SELECT stream, url from rw_stream_list WHERE machineid=?", [reg.getSetting('machine-id')], force_double_array=True)

	if len(service_streams) == 0:
		Notify('Streaming Error!', 'Could not find any viable links')
		return False
	if not ignore_prefered and reg.getBoolSetting('enable-autoplay') and reg.getBoolSetting('enable-autorank'):

		for attempt in range(1,4):
			log('Trying prefered host attempt: %s', attempt)
			try:
				row =  DB.query("SELECT url from rw_stream_list WHERE machineid=? ORDER BY priority ASC LIMIT ?,1",[attempt,reg.getSetting('machine-id')])
				host = row[0]
				resolved_url = SCR.resolveStream(host)
				break
			except:
				resolved_url = None
				pass
		if not resolved_url:
			log("Failed resolving prefered host, will ask for another mirror")
			Notify('Streaming Error!', 'Autoplay failed, select a different Stream')
			resolved_url = ShowStreamSelect(SCR, service_streams)
	else:
		log("Asking for a mirror")
		resolved_url = ShowStreamSelect(SCR, service_streams)

	setLastPath(_name)
	try:	
		log("Attempting to stream: %s", resolved_url)
		WatchStreamSource(name,resolved_url)
	except:
		log("Failed launching stream: %s", resolved_url, level=0)
		Notify('Streaming Error!', 'Selected mirror bailed, try a different Stream')


def ShowStreamSelect(SCR, service_streams, auto=False):
	global STREAM_SELECTION
	streams = []
	options = []
	dialog = xbmcgui.Dialog()
	for stream in service_streams:
		streams.append(stream[0])
		options.append(stream[1])
	stream_select = dialog.select('Select mirror', streams)
	if stream_select < 0:
		return False
	stream = options[stream_select]
	STREAM_SELECTION = streams[stream_select]
	#print "Selection is: %s" % STREAM_SELECTION
	resolved_url = SCR.resolveStream(stream)
	return resolved_url

def WatchEpisode(name, action, ignore_prefered = False):
	log('Attempting to stream: %s' % str(name))
	if name == getLastPath():
		ignore_prefered = True
	_name = name
	DB.connect()
	DB.execute("DELETE FROM rw_stream_list WHERE machineid=?", [reg.getSetting('machine-id')])
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	SCR.getStreamsByService(action)

	if reg.getBoolSetting('enable-autorank'):
		service_streams = DB.query("SELECT stream, url from rw_stream_list WHERE machineid=? ORDER BY priority ASC", [reg.getSetting('machine-id')], force_double_array=True)
	else:
		service_streams = DB.query("SELECT stream, url from rw_stream_list WHERE machineid=?", [reg.getSetting('machine-id')], force_double_array=True)

	if not ignore_prefered and reg.getBoolSetting('enable-autoplay') and reg.getBoolSetting('enable-autorank'):
		for attempt in range(1,4):
			log('Trying prefered host attempt: %s', attempt)
			try:
				row =  DB.query("SELECT url from rw_stream_list WHERE machineid=? ORDER BY priority ASC LIMIT ?,1",[attempt,reg.getSetting('machine-id')])
				host = row[0]
				resolved_url = SCR.resolveStream(host)
				break
			except:
				resolved_url = None
				pass
		if not resolved_url:
			log("Failed resolving prefered host, will ask for another mirror")
			Notify('Streaming Error!', 'Autoplay failed, select a different Stream')
			resolved_url = ShowStreamSelect(SCR, service_streams)
	else:
		log("Asking for a mirror")
		resolved_url = ShowStreamSelect(SCR, service_streams)
	setLastPath(_name)
	try:	
		log("Attempting to stream: %s", resolved_url)
		WatchStreamSource(name,resolved_url)
	except:
		log("Failed launching stream: %s", resolved_url, level=0)
		Notify('Streaming Error!', 'Selected mirror bailed, try a different Stream')


def StreamSource(name,url, media=None, idFile=None):
	log('Attempting to stream url: %s' % str(url))	
	WaitIf()
	try:
		meta = VDB.getMetaData(media, idFile)
		log(meta)
	except: 
		meta = None
	if meta:
		icon = meta['icon_url']
		thumb = meta['poster_url']
		title = meta['title']
		plot = meta['plot']
		runtime = meta['runtime']
	else:
		icon = 'DefaultVideoBig.png'
		thumb = ''
		title = name
		plot = ''
		runtime = ''
	infoLabels = {
		'Title': name,
		'Genre': 'stream: ' + STREAM_SELECTION,
		'plotoutline': STREAM_SELECTION, 
		'plot': STREAM_SELECTION
	}
	list_item = xbmcgui.ListItem(title, iconImage=icon, thumbnailImage=thumb, path=str(url))
	list_item.setProperty( "IsPlayable", "true" )
	list_item.setInfo('video', infoLabels=infoLabels)
	list_item.setThumbnailImage(thumb)

	try:
		xbmcplugin.setResolvedUrl(int(sys.argv[ 1 ]),True,list_item)
		return True
	except:
		log('Streaming failed to launch, no response from servier')
		Notify("Streaming failed", "Streaming failed")
		return False

def WatchStreamSource(name,url, idFile=None):
	global STREAM_SELECTION
	log('Attempting to stream url: %s' % str(url))	
	thumb = ''
	WaitIf()
	infoLabels = {
		'Title': name,
		'Genre': 'stream: ' + STREAM_SELECTION,
		'plotoutline': STREAM_SELECTION, 
		'plot': STREAM_SELECTION
	}
	list_item = xbmcgui.ListItem(name, iconImage="DefaultVideoBig.png", thumbnailImage=thumb, path=str(url))
	list_item.setProperty( "IsPlayable", "true" )
	list_item.setInfo('video', infoLabels=infoLabels)
	try:
		
		playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
		playlist.clear()
		playlist.add(url, list_item)
		
		xbmc.Player().play(playlist)
		return True
	except:
		log('Streaming failed to launch, no response from servier')
		Notify("Streaming failed", "Streaming failed")
		return False



###########################
### Subscriptions	###
###########################

def ViewTVSubscriptions(): #Show Subscriptions
	DB.connect()
	rows = DB.query("SELECT rw_shows.showid, rw_shows.showname, enabled, rw_subscriptions.subscriptionid FROM rw_subscriptions JOIN rw_shows ON rw_subscriptions.showid=rw_shows.showid ORDER BY rw_shows.showname ASC", force_double_array=True)

	for row in rows:
		showid = urllib.quote_plus(str(row[0]))
		showname = urllib.quote_plus(str(row[1]))
		commands = []
		cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 2111, showid, showname)
		commands.append(('Update Subscription', cmd, ''))  
		cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 2112, showid, showname)
		commands.append(('Toggle Enabled', cmd, '')) 
		cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 2113, showid, showname)
		commands.append(('Merge Subscription Into..', cmd, '')) 
		cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 2114, showid, showname)
		commands.append(('Delete Subscription', cmd, ''))  
		if str2bool(str(row[2])):
			AddOption('[B]'+str(row[1])+'[/B]', False, 2111, showid, showname,contextMenuItems=commands)
		else:
			AddOption('[COLOR red]'+str(row[1])+'[/COLOR]', False, 2111, showid, showname,contextMenuItems=commands)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))



def toggleSubscription(showid):
	DB.connect()
	DB.execute("UPDATE rw_subscriptions SET enabled=ABS(enabled-1) WHERE showid=?", [showid])
	DB.commit()
	xbmc.executebuiltin("Container.Refresh")

def mergeSubscription(showid):
	DB.connect()
	dialog = xbmcgui.Dialog()
	merge_from = showid
	rows = DB.query("SELECT rw_shows.showid, rw_shows.showname FROM rw_subscriptions JOIN rw_shows ON rw_subscriptions.showid=rw_shows.showid WHERE rw_shows.showid !=? ORDER BY rw_shows.showname ASC", [showid], force_double_array=True)
	options = []
	option_ids = []
	for row in rows:
		options.append(row[1])
		option_ids.append(row[0])
	option = dialog.select("Select a Subscription to merge into: ", options)
	if option < 0:
		return True
	merge_to = option_ids[option]
	log("Merging " + str(showid) + " TO " + str(merge_to))
	DB.execute("INSERT INTO rw_showlinks(showid, service, url) SELECT ?, src.service, src.url FROM rw_showlinks AS src WHERE src.showid=?", [merge_to, merge_from])
	DB.execute("DELETE FROM rw_subscriptions WHERE showid=?", [merge_from])
	DB.commit()
	xbmc.executebuiltin("Container.Refresh")

def SubscribeShow(name):
	showid = name
	DB.connect()
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	imdb = SCR.resolveIMDB(showid=showid)
	try:
		DB.execute("INSERT INTO rw_subscriptions(showid) VALUES(?)", [showid])
		DB.commit()
		row = DB.query("SELECT showname FROM rw_shows where showid=?", [showid])
		name = str(row[0])
		log("Subscribe to %s", name)
		Notify("Subscription Added", name)
	except Exception, e:
		Notify("Subscription Failed", 'ERROR: %s' % e)

def UnsubscribeShow(name):
	showid = name
	DB.connect()
	row = DB.query("SELECT showname FROM rw_shows where showid=?", [showid])
	name = str(row[0])
	dialog = xbmcgui.Dialog()
	if dialog.yesno("Unsubscribe", "Do you want to unsubscribe to "+name+"?"):
		log("Unsubscribing: %s", name)
		rows = DB.query("SELECT episodeid FROM rw_episodes WHERE showid=?", [showid], force_double_array=True)
		ids=[]
		for row in rows:
			ids.append(str(row[0])) 
		SQL = "SELECT * from rw_episodelinks WHERE episodeid in ( %s )" % ','.join(ids)
		DB.execute(SQL)
		DB.execute("DELETE FROM rw_episodes WHERE showid=?", [showid])
		DB.execute("DELETE FROM rw_subscriptions where showid=?", [showid])
		DB.commit()
		### remove strm files here ###
		xbmc.executebuiltin("Container.Refresh")

		

def DeleteAllSubscriptions(): #2430
	log('Clearing Subscriptions', level=0)
	dialog = xbmcgui.Dialog()
	if dialog.yesno("Delete Subscriptions", "Do you want to unsubscribe to all shows?"):
		log("Unsubscribing to All", level=0)
		#DB.connect()
		#DB.execute("DELETE FROM rw_subscriptions")
		#DB.commit()
		# loop through above #

def UpdateSingleShow(showid, name):
	DB.connect()
	log("Update subscription by id: %s" % name)
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	SCR.updateSubscriptionById(showid, name)
	showpath = os.path.join(xbmc.translatePath( TV_SHOWS_PATH + SCR.cleanName(name, remove_year=True)), '')
	log('Scan new show: %s' % showpath)
	xbmc.executebuiltin('UpdateLibrary(video,' + showpath + ')')

def UpdateAvailableTVShows(silent=False):
	_silent=silent
	DB.connect()
	if not silent:
		dialog = xbmcgui.Dialog()
		if not dialog.yesno("Cache Shows", "Do you want to update the cache? \nThis will take a few minuts."):
			return False
	updateJobStatus('TV update')
	if reg.getBoolSetting('enable-silent-updates') or silent:
		silent=True
	log("Downloading available shows from providers")
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)	
	SCR.getShows(silent)
	DB.execute("UPDATE rw_status SET updating=0, job=''")
	DB.commit()
	if _silent:
		Notify('Download Complete!', 'TV Shows updated.')


def UpdateTVSubscriptions(silent=False):
	_silent=silent
	log("Updating Subscriptions")
	DB.connect()
	if checkUpdateStatus():
		log("Donwload in progress.")
		Notify('Please try again!', 'Donwload in progress, check status.')
		return
	if not silent:
		dialog = xbmcgui.Dialog()
		if not dialog.yesno("Update Subscriptions", "Do you want to update the subscriptions? \nThis will take a few minuts."):
			return False
	updateJobStatus('Subscription update')
	if reg.getBoolSetting('enable-silent-updates') or silent:
		silent=True
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)	
	SCR.updateSubscriptions(silent)
	DB.execute("UPDATE rw_status SET updating=0, job=''")
	DB.commit()
	if _silent:
		Notify('Download Complete!', 'Subscriptions updated.')

def UpdateAvailableMovies(silent=False):
	_silent=silent
	DB.connect()
	row = DB.query("SELECT updating FROM rw_status")
	if checkUpdateStatus():
		log("Donwload in progress.")
		Notify('Please try again!', 'Donwload in progress, check status.')
		return
	if not silent:
		dialog = xbmcgui.Dialog()
		if not dialog.yesno("Cache movies", "Do you want to update the cache? \nThis will take a long time on the first run."):
			return False
	updateJobStatus('Movie update')
	if reg.getBoolSetting('enable-silent-updates') or silent:
		silent=True
	print "Downloading available movies from providers"

	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)	
	SCR.getMovies(silent)
	DB.execute("UPDATE rw_status SET updating=0, job=''")
	DB.commit()
	if _silent:
		Notify('Download Complete!', 'Movies updated.')

def checkUpdateStatus():
	try:
		row = DB.query("SELECT updating FROM rw_status")
		if row[0] == 1:
			return True
	except: pass
	return False

def updateJobStatus(job):
	if job == 'Movie update':
		ts = 'last_movie_update'
	elif job == 'TV update':
		ts = 'last_tvshow_update'
	else:
		ts = 'last_subscription_update'
	
	if DB_TYPE == 'sqlite':
		DB.execute("UPDATE rw_status SET updating=1, job=?,"+ts+"=DATETIME('now')", [job])
	else:
		DB.execute("UPDATE rw_status SET updating=1, job=?,"+ts+"=NOW()", [job])
	DB.commit()
	

def ImportMovie(name):
	DB.connect()
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)	
	SCR.importMovie(name)
	Notify("Movie Added", name)

def UpdateMovies(silent=False):
	print "Updating Movies"

def ShowRecentlyAired():
	print "Nav to RecentlyAired"
	xbmc.executebuiltin('ActivateWindow(10025,"'+RECENTLY_AIRED_PATH+'")')

def ToggleProvider(providerid):
	log("Toggle enabled: %s", str(providerid))
	DB.connect()
	DB.execute("UPDATE rw_providers SET enabled = ABS(enabled - 1) WHERE providerid=?", [providerid])
	DB.commit()
	xbmc.executebuiltin("Container.Refresh")

###################
### Auto-update ###
###################

def AutoUpdateSubscriptions():
	log("Updating TV Show Subscriptions", level=0)
	UpdateTVSubscriptions(silent=True)
	while checkUpdateStatus():
		xbmc.sleep(30000)
	log("Update Complete!", level=0)
	UpateVideoLibrary()
	DownloadArtwork()

def UpateVideoLibrary():
	if reg.getBoolSetting('update_library'):
		log("Update videolibrary: %s", TV_SHOWS_PATH, level=0)
		xbmc.executebuiltin('UpdateLibrary(video,' + TV_SHOWS_PATH + ')')

def DownloadArtwork():
	if reg.getBoolSetting('update_artwork'):
		log("Downloading Artwork", level=0)
		xbmc.executebuiltin('RunScript("script.artwork.downloader", "mode=custom&silent=true&mediatype=tvshow")')		

def AutoUpdateTVShows():
	log("Updating TV Shows", level=0)
	UpdateAvailableTVShows(silent=True)

def AutoUpdateMovies():
	log("Updating Movies", level=0)
	UpdateAvailableMovies(silent=True)


def ProcessQueue():
	log("Process Queue")
	DB.connect()
	row = DB.query("SELECT command, id FROM rw_command_queue WHERE completed=0 ORDER BY qid ASC LIMIT 1")
	try:
		if row[0]=='movielookup':
			ProcessMovie(row[1])
	except:
		pass

def ProcessMovie(movieid):
	title = ''
	year = ''
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	imdb = SCR.resolveIMDB(movieid)
	url = "http://imdbapi.org/?id=%s&type=xml&plot=none&episode=0&lang=en-US&aka=simple&release=simple&business=0&tech=0" % imdb
	req = urllib2.Request(url)
	res = urllib2.urlopen(req)
	body = res.read()
	soup = BeautifulSoup(body)
	rating = soup.find('rating').string
	director = soup.find('director').string
	writer = soup.find('writer').string
	released = soup.find('release_data').string

###################
### Support Fx	###
###################

def timestamp(d):
	import time
	return time.mktime(d.timetuple())

def getNextRun(last, f, delay=0):
	from datetime import datetime, date
	import math
	seconds =  f * 3600
	delay = delay * 60;
	today = date.today()
	zero = timestamp(last)
	now = timestamp(datetime.now())
	delta = (now - zero) / (seconds)
	offset = math.ceil(delta)
	next =  offset * seconds + (zero + delay)
	next = math.floor(next / 360) * 360
	next = datetime.fromtimestamp(next)
	return str(next)

def ViewStatus():
	print "view status"
	DB.connect()
	row = DB.query("SELECT updating, last_tvshow_update, last_movie_update, last_subscription_update, job FROM rw_status")
	title = 'Status'
	maude_status = ' - '
	if reg.getBoolSetting('auto_update'):
		autoupdater_status = 'Enabled'
	else:
		autoupdater_status = 'Disabled'
	try:
		if row[0]==1:
			donnie_status = 'Running'
		else:
			donnie_status = 'Idle'
		timers1 = [4, 8, 12, 24]
		timers2 = [24, 48, 120, 168]
		last_tvshow_update			=row[1]
		interval = timers2[int(reg.getSetting('update_tvshowcache_timer'))]
		next_tvshow_update			= getNextRun(last_tvshow_update, interval)
	
		last_movie_update			=row[2]
		interval = timers2[int(reg.getSetting('update_moviecache_timer'))]
		next_movie_update			= getNextRun(last_movie_update, interval, 60)

		last_subscription_update		=row[3]
		interval = timers1[int(reg.getSetting('update_tvshows_timer'))]
		next_subscription_update		= getNextRun(last_subscription_update, interval, 30)
		job					=row[4]
	except:
		donnie_status 				= '-'
		last_tvshow_update			= '-'
		next_tvshow_update			= '-'	
		last_movie_update			= '-'
		next_movie_update			= '-'
		last_subscription_update		= '-'
		next_subscription_update		= '-'
		job					= '-'
	
	status = {
		'icefilms' : { 'tvshows' : '', 'movies' : '' },
		'wareztuga' : { 'tvshows' : '', 'movies' : '' },
		'1channel' : { 'tvshows' : '', 'movies' : '' },
		'vidics' : { 'tvshows' : '', 'movies' : '' },
		'alluc' : { 'tvshows' : '', 'movies' : '' },
		'tubeplus' : { 'tvshows' : '', 'movies' : '' },
	}	
	rows = DB.query("SELECT * FROM rw_update_log", force_double_array=True)
	for row in rows:
		try:
			p = row[1]
			s = row[0]
			v = row[2]
			status[p][s]=v
		except: pass
	text = '''
	Services:	
	------------------------------------------
	[B]Maude[/B]:				%s
	[B]AutoUpdater[/B]: 			%s
	[B]Donnie[/B]: 				%s - %s
	
	Donnie update times:
	------------------------------------------	
	[B]Last TV Show Index[/B]: 		%s
	[B]Last Subscription Update[/B]: 	%s
	[B]Last Movie Index[/B]: 		%s

	[B]Next TV Show Index[/B]: 		%s
	[B]Next Subscription Update[/B]: 	%s
	[B]Next Movie Index[/B]: 		%s

	Provider update times:
	------------------------------------------	
	[B]Icefilms - TV[/B]: 			%s
	[B]Icefilms - Movies[/B]: 		%s
	[B]1Channel - TV[/B]: 			%s
	[B]1Channel - Movies[/B]:		%s	
	[B]WarezTuga - TV[/B]: 			%s
	[B]WarezTuga - Movies[/B]: 		%s
	[B]Vidics - TV[/B]: 			%s
	[B]Vidics - Movies[/B]:			%s
	[B]TubePlus - TV[/B]: 			%s
	[B]TubePlus - Movies[/B]:		%s
	[B]Alluc - TV[/B]: 			%s
	[B]Alluc - Movies[/B]:			%s
	''' % (maude_status, maude_status,donnie_status,job,last_tvshow_update,last_subscription_update,last_movie_update, next_tvshow_update,next_subscription_update,next_movie_update,status['icefilms']['tvshows'], status['icefilms']['movies'], status['1channel']['tvshows'], status['1channel']['movies'], status['wareztuga']['tvshows'], status['wareztuga']['movies'], status['vidics']['tvshows'], status['vidics']['movies'], status['tubeplus']['tvshows'], status['tubeplus']['movies'], status['alluc']['tvshows'], status['alluc']['movies'])
	TB = TextBox()
	TB.show(title, text)


def ViewLOG(show=True):
	
	logfile = xbmcpath('special://temp', 'xbmc.log')
	log = readfile(logfile)
	log = re.sub('<host>(.+?)</host>', '<pass>******</pass>', log)
	log = re.sub('<name>(.+?)</name>', '<name>******</name>', log)
	log = re.sub('<user>(.+?)</user>', '<user>******</user>', log)
	log = re.sub('<pass>(.+?)</pass>', '<pass>******</pass>', log)
	
	if show:	
		TB = TextBox()
		TB.show('Support Request', log)
	else:
		return log

def SubmitLog():
	xbmc.executebuiltin('RunScript(script.xbmc.debug.log, "")')


def ViewFAQ(id):
	faq = xbmcpath(rootpath, 'resources/faq.xml')
	soup = readfile(faq, soup=True)
	heading = soup.find('heading', {'id':id})
	title = heading['title']
	text = heading.string
	TB = TextBox()
	TB.show(title, text)

def WatchTVResults(name, action):
	log('Listing TV by: %s, %s' % (action, name))
	DB.connect()
	enabled_providers = []
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	for index in range(0, len(SCR.activeScrapers)):
		enabled_providers.append("'%s'" % SCR.getScraperByIndex(index).service)
	str_filter = ','.join(enabled_providers)
	if action=='az':
		SQL = "SELECT rw_shows.showname, rw_shows.showid FROM rw_shows JOIN rw_showlinks ON rw_shows.showid=rw_showlinks.showid WHERE CHR=? AND (rw_showlinks.service in ("+str_filter+")) GROUP BY rw_shows.showname ORDER BY rw_shows.showname ASC"
		if name=='#1234':
			search = '1'
		else:
			search = name
	elif action=='genre':
		SQL = "SELECT rw_shows.showname, rw_shows.showid FROM rw_shows JOIN rw_showgenres ON rw_showgenres.showid=rw_shows.showid JOIN rw_showlinks ON rw_shows.showid=rw_showlinks.showid WHERE rw_showgenres.genre=? AND (rw_showlinks.service in ("+str_filter+")) GROUP BY rw_shows.showname ORDER BY rw_shows.showname ASC"
		search = name
	elif action=='search':
		if DB_TYPE == 'mysql':
			search = name
			SQL = "SELECT rw_shows.showname, rw_shows.showid FROM rw_shows JOIN rw_showlinks ON rw_shows.showid=rw_showlinks.showid WHERE showname REGEXP ? AND (rw_showlinks.service in ("+str_filter+")) GROUP BY rw_shows.showname ORDER BY rw_shows.showname ASC"
		else:
			SQL = "SELECT rw_shows.showname, rw_shows.showid FROM rw_shows JOIN rw_showlinks ON rw_shows.showid=rw_showlinks.showid WHERE showname LIKE ? AND (rw_showlinks.service in ("+str_filter+")) GROUP BY rw_shows.showname ORDER BY rw_shows.showname ASC"
			search = '%'+name+'%'

	rows = DB.query(SQL, [search], force_double_array=True)
	for row in rows:
		commands = []
		try:
			
			cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 2115, urllib.quote_plus(str(row[1])), '')
			commands.append(('Subscribe to show', cmd, ''))    		
			AddOption(row[0], True, 1190, str(row[1]), contextMenuItems=commands)
		except:
			commands = []
			pass

	xbmcplugin.endOfDirectory(int(sys.argv[1]))


def WatchTVTraktResults(name, url=None):
	from donnie.trakt import Trakt
	Tr = Trakt(reg)
	META = metahandlers.MetaData()
	if name=='trending':
		trending = Tr.getTrendingShows()
		for show in trending:
			commands = []
			if USE_META:
				try:
					imdb =  show['imdb_id']
					data = META.get_meta('tvshow', show['title'], imdb_id=imdb)
				except: data=None
				if data:
					icon = data['cover_url']
					fanart = data['backdrop_url']
				else:
					icon=show['images']['poster']
					fanart=show['images']['fanart']
			else:
				data = None
				icon=show['images']['poster']
				fanart=show['images']['fanart']
			commands = addCommand(commands, 'Add to Trakt Watchlist', 1236, show['imdb_id'])
			commands = addCommand(commands, 'Add to IMDB Watchlist', 1241, show['imdb_id'])
			AddOption("%s (%s)" % (show['title'], show['year']), True, 1159, show['title'], iconImage=icon, fanart=fanart, meta=data, contextMenuItems=commands)

	elif name=='watchlist':
		watchlist = Tr.getWatchlistShows()
		for show in watchlist:
			commands = []
			if USE_META:
				try:
					imdb =  show['imdb_id']
					data = META.get_meta('tvshow', show['title'], imdb_id=imdb)
				except: data=None
				if data:
					icon = data['cover_url']
					fanart = data['backdrop_url']
				else:
					icon=show['images']['poster']
					fanart=show['images']['fanart']
			else:
				data = None
				icon=show['images']['poster']
				fanart=show['images']['fanart']
			commands = addCommand(commands, 'Remove from Trakt Watchlist', 1237, show['imdb_id'])
			commands = addCommand(commands, 'Add to IMDB Watchlist', 1241, show['imdb_id'])
			AddOption("%s (%s)" % (show['title'], show['year']), True, 1159, show['title'], iconImage=icon, fanart=fanart, meta=data, contextMenuItems=commands)

	elif name=='custom':
		lists = Tr.getCustomLists()
		for li in lists:
			AddOption(li['name'],True, 1132, 'user-custom-list', Tr.username + '/' + li['slug'])

	elif name=='list':
		custom = Tr.getCustomList(url)
		shows = custom['items']
		for show in shows:
			commands = []
			if USE_META:
				try:
					imdb =  show['imdb_id']
					data = META.get_meta('tvshow', show['title'], imdb_id=imdb)
				except: data=None
				if data:
					icon = data['cover_url']
					fanart = data['backdrop_url']
				else:
					icon=show['images']['poster']
					fanart=show['images']['fanart']
			else:
				data = None
				icon=show['images']['poster']
				fanart=show['images']['fanart']
			AddOption("%s (%s)" % (show['title'], show['year']), True, 1159, show['title'], iconImage=icon, fanart=fanart, meta=data)
	else:
		recommended = Tr.getRecommendedShows()
		popular =  recommended['activity']

		for i in range(0,len(popular)):
			commands = []
			show = popular[i]['show']
			if USE_META:
				try:
					imdb =  show['imdb_id']
					data = META.get_meta('tvshow', show['title'], imdb_id=imdb)
				except: data=None
				if data:
					icon = data['cover_url']
					fanart = data['backdrop_url']
				else:
					icon=show['images']['poster']
					fanart=show['images']['fanart']
			else:
				data = None
				icon=show['images']['poster']
				fanart=show['images']['fanart']			
			AddOption("%s (%s)" % (show['title'], show['year']), True, 1159, show['title'], iconImage=icon, fanart=fanart, meta=data)
	setView('default-tvshow-view')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))


def WatchTVIMDBResults(name):
	from donnie.imdb import IMDB
	Imdb = IMDB(reg)
	META = metahandlers.MetaData()
	if name=='popular':
		shows = Imdb.getPopular()
	elif name=='watchlist':
		shows = Imdb.getWatchList()

	for show in shows['list']:
		commands = []
		if len(show['extra'])>6:
			if USE_META:
				try:
					url = show['url']
					imdb =  url[7:len(url)-1]
					data = META.get_meta('tvshow', show['title'], imdb_id=imdb)
				except: data=None
				if data:
					icon = data['cover_url']
					fanart = data['backdrop_url']
				else:
					icon=''
					fanart=''
			else:
				data = None
				icon=''
				fanart=''
			title = "%s %s" % (show['title'], show['extra'])
			if name == 'watchlist':
				commands = addCommand(commands, 'Remove from IMDB Watchlist', 1242, imdb)
				commands = addCommand(commands, 'Add to Trakt Watchlist', 1231, imdb)
			else:
				commands = addCommand(commands, 'Add to Trakt Watchlist', 1231, imdb)
				commands = addCommand(commands, 'Add to IMDB Watchlist', 1241, imdb)
				
			AddOption(title, True, 1159, show['title'], iconImage=icon, fanart=fanart, meta=data,contextMenuItems=commands)

	setView('default-tvshow-view')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))


def GetEpisodeList(showid):
	DB.connect()
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	META = metahandlers.MetaData()
	SCR.getEpisodes(showid)
	row = DB.query("SELECT showname, imdb FROM rw_shows WHERE showid=?", [showid])
	tvshowtitle = row[0]
	imdb_id = row[1]
	if USE_META:
		data = META.get_meta('tvshow', tvshowtitle, imdb_id=imdb_id)
	else:
		data = None
	if data:
		icon = data['cover_url']
		fanart = data['banner_url']
	else:
		icon = ''
		fanart = ''
	
	if DB_TYPE=='mysql':
		SQL = "SELECT episodeid, name, LPAD(season, 2, 0) as season, LPAD(episode, 2, 0) as episode FROM rw_episodes WHERE showid=? ORDER BY season, episode ASC"
	else:
		SQL = "SELECT episodeid, name, substr('00' || season, -2, 2) AS season, substr('00' || episode, -2, 2) AS episode FROM rw_episodes WHERE showid=? ORDER BY season, episode ASC" 
	
	rows = DB.query(SQL, [showid], force_double_array=True) 
	for row in rows:
		commands = []
		if re.match("^\d{1,2}x\d{1,2} ", row[1]):
			name = re.sub("^\d{1,2}x\d{1,2} ", "", row[1])	
		else:
			name = row[1]
		name = "%sx%s - %s" % (row[2], row[3], name)
		AddOption(name, True, 50, str(row[0]), action='tvshow', iconImage=icon, fanart=fanart, meta=data, contextMenuItems=commands)

	xbmcplugin.endOfDirectory(int(sys.argv[1]))


def WatchMovieResults(name, action):
	log('Listing Movies by: %s, %s' % (action, name))
	DB.connect()
	enabled_providers = []
	
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	for index in range(0, len(SCR.activeScrapers)):
		enabled_providers.append("'%s'" % SCR.getScraperByIndex(index).service)
	str_filter = ','.join(enabled_providers)
	if action=='az':
		SQL = "SELECT movie FROM rw_movies WHERE CHR=? AND provider IN ("+str_filter+") GROUP BY movie ORDER BY movie ASC"
		if name=='#1234':
			search = '1'
		else:
			search = name
	elif action=='genre':	
		SQL = "SELECT rw_movies.movie FROM rw_movies JOIN rw_moviegenres ON rw_movies.movieid=rw_moviegenres.movieid WHERE rw_moviegenres.genre=? AND rw_movies.provider IN ("+str_filter+") GROUP BY rw_movies.movie ORDER BY rw_movies.movie ASC"
		search = name
	elif action=='search':
		if DB_TYPE == 'mysql':
			SQL = "SELECT movie FROM rw_movies WHERE movie REGEXP ? AND provider IN ("+str_filter+") GROUP BY movie ORDER BY movie ASC"
			search = name
		else:
			SQL = "SELECT movie FROM rw_movies WHERE movie LIKE ? AND provider IN ("+str_filter+") GROUP BY movie ORDER BY movie ASC"
			search = '%'+name+'%'
	rows = DB.query(SQL, [search], force_double_array=True)
	for row in rows:
		try:
			commands = []
			cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 2500, urllib.quote_plus(row[0]), '')
			commands.append(('Add Moive to Library', cmd, ''))    		
			AddOption(str(row[0]), False, 50, str(row[0]), action='movie', contextMenuItems=commands)
		except:
			pass
	#if reg.getBoolSetting('enable-default-views'):
	#	xbmc.executebuiltin("Container.SetViewMode("+reg.getSetting('default-movie-view')+")")
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchMovieTraktResults(name, url=None):
	from donnie.trakt import Trakt
	Tr = Trakt(reg)
	META = metahandlers.MetaData()
	if name=='trending':
		trending = Tr.getTrendingMovies()
		for movie in trending:
			commands = []
			if USE_META:
				try: 
					imdb =  movie['imdb_id']
					data = META.get_meta('movie', movie['title'], imdb_id=imdb)
				except: data=None
				if data:
					icon = data['cover_url']
					fanart = data['backdrop_url']
					cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1231, movie['imdb_id'], '')			
					commands.append(('Add to Trakt Watchlist', cmd, ''))
					cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1241, movie['imdb_id'], '')				
					commands.append(('Add to IMDB Watchlist', cmd, ''))
				else:
					icon = movie['images']['poster']
					fanart = movie['images']['fanart']
					commands = []
					
			else:
				data = None
				icon = movie['images']['poster']
				fanart = movie['images']['fanart']

			AddOption("%s (%s)" % (movie['title'], movie['year']), True, 1259, movie['title'], iconImage=movie['poster'], fanart=movie['images']['fanart'], meta=data, contextMenuItems=commands)

	elif name=='watchlist':
		watchlist = Tr.getWatchlistMovies()
		for movie in watchlist:
			commands = []
			if USE_META:
				try: 
					imdb =  movie['imdb_id']
					data = META.get_meta('movie', movie['title'], imdb_id=imdb)
				except: data=None
				if data:
					icon = data['cover_url']
					fanart = data['backdrop_url']

				else:
					icon = movie['images']['poster']
					fanart = movie['images']['fanart']
			else:
				data = None
				icon = movie['images']['poster']
				fanart = movie['images']['fanart']
			cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1235, movie['imdb_id'], '')			
			commands.append(('Remove From Trakt Watchlist', cmd, ''))
			cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1241, imdb, '')				
			commands.append(('Add to IMDB Watchlist', cmd, ''))
			AddOption("%s (%s)" % (movie['title'], movie['year']), True, 1259, movie['title'], iconImage=icon, fanart=fanart, meta=data,contextMenuItems=commands)

	elif name=='popular':
		lists = Tr.getPopularLists()
		
		for li in lists:
			commands = []
			cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1233, li['user'], li['slug'])			
			commands.append(('Like This List', cmd, ''))
			url = "%s/%s" % (li['user'], li['slug'])
			meta = {'plot' : li['description'], 'cover_url' : li['poster']}
			AddOption(li['name'],True, 1232, url, iconImage=li['poster'], meta=meta, contextMenuItems=commands)

	elif name=='custom':
		lists = Tr.getCustomLists()
		
		for li in lists:
			
			AddOption(li['name'],True, 1232, 'user-custom-list', Tr.username + '/' + li['slug'])

	elif name=='liked':
		lists = Tr.getLikedLists()
		for li in lists:
			commands = []
			cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1234, li['user'], li['slug'])			
			commands.append(('Unlike This List', cmd, ''))
			url = "%s/%s" % (li['user'], li['slug'])
			meta = {'plot' : li['description'], 'cover_url' : li['poster']}
			AddOption(li['name'],True, 1232, url, iconImage=li['poster'], meta=meta, contextMenuItems=commands)
	elif name=='list':
		custom = Tr.getCustomList(url)
		movies = custom['items']
		for movie in movies:
			if movie['type'] == 'movie':
				commands = []
				if USE_META:
					try: 
						imdb = movie['movie']['imdb_id']
						data = META.get_meta('movie', movie['movie']['title'], imdb_id=imdb)
					except: data=None
					if data:
						icon = data['cover_url']
						fanart = data['backdrop_url']
					else:
						icon = movie['movie']['images']['poster']
						fanart = movie['movie']['images']['fanart']
				else:
					data = None
					icon = movie['images']['poster']
					fanart = movie['images']['fanart']
				cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1231, movie['movie']['imdb_id'], '')			
				commands.append(('Add to Trakt Watchlist', cmd, ''))
				cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1241, movie['imdb_id'], '')				
				commands.append(('Add to IMDB Watchlist', cmd, ''))
				AddOption("%s (%s)" % (movie['movie']['title'], movie['movie']['year']), True, 1259, movie['movie']['title'], iconImage=icon, fanart=fanart, meta=data, contextMenuItems=commands)

	else:
		recommended = Tr.getRecommendedMovies()
		popular =  recommended['activity']
		for i in range(0,len(popular)):
			if USE_META:
				commands = []
				movie = popular[i]['movie']
				try: 
					imdb =  movie['imdb_id']
					data = META.get_meta('movie', movie['title'], imdb_id=imdb)
				except: data=None
				if data:
					icon = data['cover_url']
					fanart = data['backdrop_url']
				else:
					icon = movie['images']['poster']
					fanart = movie['images']['fanart']
			else:
				data = None
				icon = movie['images']['poster']
				fanart = movie['images']['fanart']
			cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1231, movie['imdb_id'], '')			
			commands.append(('Add to Trakt Watchlist', cmd, ''))
			cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1241, movie['imdb_id'], '')				
			commands.append(('Add to IMDB Watchlist', cmd, ''))
			AddOption("%s (%s)" % (movie['title'], movie['year']), True, 1259, movie['title'], iconImage=icon, fanart=fanart, meta=data, contextMenuItems=commands)
	setView('default-movie-view')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchTVNewReleases():
	DB.connect()
	META = metahandlers.MetaData()
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	episodes = SCR.getNewEpisodes()
	for episode in episodes:
		try:
			if USE_META:
				temp = re.search("^(.+?) (\d{1,3})x(\d{1,4}) ", episode[1])
				if not temp: temp = re.search("^(.+?) S(\d{1,3})E(\d{1,4}): ", episode[1])
				if not temp: temp = re.search("^(.+?) (\d{1,3})x(\d{1,4})$", episode[1])
				'''temp = re.search("^(.+?) (\d{1,3})x(\d{1,3}) ", episode[1])
				if temp:
					t = temp.group(1)
					s = int(temp.group(2))				
					e = int(temp.group(3))
				temp = re.search("^(.+?) S(\d{1,3})E(\d{1,3}): ", episode[1])'''
				if temp:
					t = temp.group(1)
					s = int(temp.group(2))				
					e = int(temp.group(3))
				if t:
					tv_meta = META.get_meta('tvshow',t)
					data=META.get_episode_meta(t, tv_meta['imdb_id'], s, e)
					fanart = data['backdrop_url']
					icon = ''
				t = None
			else:
				data = None
				icon = ''
				fanart = ''

			link = "%s://%s" % (episode[0], episode[2])

			AddOption(episode[1], True, 60, episode[1], link, iconImage=icon, fanart=fanart, meta=data)
		except Exception, e:
			print e
			icon = ''
			fanart = ''
			data = None			
			pass
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchTVSubscriptions():
	DB.connect()
	META = metahandlers.MetaData()
	rows = DB.query("SELECT rw_shows.showid, rw_shows.showname, enabled, rw_subscriptions.subscriptionid, rw_shows.imdb FROM rw_subscriptions JOIN rw_shows ON rw_subscriptions.showid=rw_shows.showid ORDER BY rw_shows.showname ASC", force_double_array=True)

	for row in rows:
		if USE_META:
			data = META.get_meta('tvshow', row[1], imdb_id=row[4])
		else:
			data = None
		if data:
			icon = data['cover_url']
			fanart = data['banner_url']
		else:
			icon = ''
			fanart = ''
		showid = urllib.quote_plus(str(row[0]))
		showname = urllib.quote_plus(str(row[1]))
		AddOption(str(row[1]), True, 1190, showid, iconImage=icon, fanart=fanart, meta=data)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchMovieIMDBResults(name):
	from donnie.imdb import IMDB
	Imdb = IMDB(reg)
	META = metahandlers.MetaData()
	
	if name=='top250':
		movies = Imdb.getTop250()
	elif name=='moviemeter':
		movies = Imdb.getMovieMeter()
	elif name=='bestpictures':
		movies = Imdb.getBestPictures()
	elif name=='watchlist':
		movies = Imdb.getWatchList()
		print movies
	for movie in movies['list']:
		commands = []
		if len(movie['extra'])==6:
			if USE_META:
				try:
					url = movie['url']
					imdb =  url[7:len(url)-1]
					data = META.get_meta('movie', movie['title'], imdb_id=imdb)
				except: data=None
				if data:
					icon = data['cover_url']
					fanart = data['backdrop_url']
			else:
				data = None
				icon = ''
				fanart = ''
			title = "%s %s" % (movie['title'], movie['extra'])
			if name == 'watchlist':
				#cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1242, imdb, '')				
				#commands.append(('Remove from IMDB Watchlist', cmd, ''))
				#cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1231, imdb, '')			
				#commands.append(('Add to Trakt Watchlist', cmd, ''))
				commands = addCommand(commands, 'Remove from IMDB Watchlist', 1242, imdb)
				commands = addCommand(commands, 'Add to Trakt Watchlist', 1231, imdb)
			else:
				#cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1231, imdb, '')			
				#commands.append(('Add to Trakt Watchlist', cmd, ''))
				#cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 1241, imdb, '')				
				#commands.append(('Add to IMDB Watchlist', cmd, ''))
				commands = addCommand(commands, 'Add to Trakt Watchlist', 1231, imdb)
				commands = addCommand(commands, 'Add to IMDB Watchlist', 1241, imdb)
			AddOption(title, True, 1259, movie['title'], iconImage=icon, fanart=fanart, meta=data, contextMenuItems=commands)
	setView('default-movie-view')	
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def addCommand(container, text, mode, name='', action=''):
	cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], mode, name, action)
	container.append((text, cmd, ''))
	return container

def addMovieIMDBWatch(imdb):
	from donnie.imdb import IMDB
	Imdb = IMDB(reg)
	Imdb.addToWatchlist(imdb)

def removeMovieIMDBWatch(imdb):
	from donnie.imdb import IMDB
	Imdb = IMDB(reg)
	Imdb.removeFromWatchlist(imdb)
	xbmc.executebuiltin("Container.Refresh")
	
def addMovieTraktWatch(imdb):
	from donnie.trakt import Trakt
	Tr = Trakt(reg)
	print Tr.watchlistMovie(imdb)

def removeMovieTraktWatch(imdb):
	from donnie.trakt import Trakt
	Tr = Trakt(reg)
	print Tr.unwatchlistMovie(imdb)
	xbmc.executebuiltin("Container.Refresh")

def addShowTraktWatch(imdb):
	from donnie.trakt import Trakt
	Tr = Trakt(reg)
	print Tr.watchlistShow(imdb)

def removeShowTraktWatch(imdb):
	from donnie.trakt import Trakt
	Tr = Trakt(reg)
	print Tr.unwatchlistShow(imdb)
	xbmc.executebuiltin("Container.Refresh")

def TraktLikeList(username, slug):
	from donnie.trakt import Trakt
	Tr = Trakt(reg)
	Tr.likeUserList(username, slug)

def TraktUnlikeList(username, slug):
	from donnie.trakt import Trakt
	Tr = Trakt(reg)
	Tr.unlikeUserList(username, slug)
	xbmc.executebuiltin("Container.Refresh")

def DragProvider(key):
	temp = key.split(":")
	drag=temp[0]
	dragid=int(temp[1])
	dragname=temp[2]

	DB.connect()
	rows = DB.query("SELECT provider, mirror, priority, providerid FROM rw_providers WHERE priority != ? ORDER BY priority ASC", [dragid])
	options = []
	for row in rows:
		name = "[B]%s.[/B] %s - %s" % (row[2], row[0], row[1])
		options.append(name)
	dialog = xbmcgui.Dialog()
	dragname = "Move: [B]%s.[/B] %s" % (dragid, dragname)
	option = dialog.select(dragname, options)
	if option < 0:
		return True
	dropid = int(rows[option][2])

	log("Move %s to %s", (dragid, dropid))
	if dragid > dropid:
		log("Move Up")
		DB.execute("UPDATE rw_providers SET priority=priority+1 WHERE priority >= ?", [dropid])
		DB.execute("UPDATE rw_providers SET priority=? WHERE priority=?",  [dropid,dragid+1])
		DB.commit()
	elif dragid < dropid:
		log("Move Down")
		DB.execute("UPDATE rw_providers SET priority=priority-1 WHERE priority > ? AND priority <= ?",[dragid, dropid])
		DB.execute("UPDATE rw_providers SET priority=? WHERE providerid =?", [dropid, drag])
		DB.commit()
	xbmc.executebuiltin("Container.Refresh")	

###################
### Addon menu 	###
###################

def AddonMenu():  #homescreen
	log('The Royal We menu', level=0)
	AddOption('Watch',True, 1000, iconImage=art+'/watch.jpg')
	AddOption('Manage',True, 2000, iconImage=art+'/manage.jpg')
	AddOption('Support',True, 3000, iconImage=art+'/support.jpg')
	AddOption('Settings',True, 4000, iconImage=art+'/settings.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchMenu():
	AddOption('TV Shows',True, 1100, iconImage=art+'/tvshows.jpg')
	AddOption('Movies',True, 1200, iconImage=art+'/movies.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchTVMenu():
	AddOption('Newest Episodes',True, 1160, iconImage=art+'/newestepisodes.jpg')
	AddOption('Subscriptions',True, 1170, iconImage=art+'/watchsubscriptions.jpg')
	AddOption('Browse A-Z',True, 1110, iconImage=art+'/a-z.jpg')
	AddOption('Browse Genres',True, 1120, iconImage=art+'/browsegenres.jpg')
	AddOption('Trakt.TV',True, 1130, iconImage=art+'/trakt.jpg')
	AddOption('IMDB',True, 1140, iconImage=art+'/imdb.jpg')
	AddOption('Search',True, 1150, iconImage=art+'/search.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchTVAZMenu():
	path = art+'/letters/'
	for character in AZ_DIRECTORIES:
		if character == '#1234': character = '1234'
		icon = path+ urllib.quote_plus(character.lower()+'.jpg')
		AddOption(character,True,1119,character,iconImage=icon)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchTVGenreMenu():
	DB.connect()
	path = art+'/genres/'
	rows = DB.query("SELECT distinct genre from rw_showgenres ORDER BY genre ASC")
	for row in rows:
		genre = row[0].lower().replace('-', '')
		if genre in ["japanese", 'none', "talkshow"]: genre = 'genre'
		icon = path+ urllib.quote_plus(genre+'.jpg')
		AddOption(row[0],True,1129, row[0],iconImage=icon)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchTVTraktMenu():
	AddOption('Trakt.tv Watchlist',True,1139, 'watchlist', 'trakt', iconImage=art+'/traktwatchlist.jpg')
	AddOption('Trakt.tv Trending',True,1139, 'trending', 'trakt', iconImage=art+'/trakttrending.jpg')
	AddOption('Trakt.tv Recommended',True, 1139, 'recommended', 'trakt', iconImage=art+'/traktrecommended.jpg')
	AddOption('Trakt.tv Personal Lists',True, 1139, 'custom', 'trakt', iconImage=art+'/traktpersonallists.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchTVIMDBMenu():
	AddOption('IMDB Watchlist',True,1149, 'watchlist', 'imdb', iconImage=art+'/imdbwatchlist.jpg')
	AddOption('IMDB Popular TV',True,1149, 'popular', 'imdb', iconImage=art+'/imdbpopulartv.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchMovieMenu():
	AddOption('Browse A-Z',True, 1210, iconImage=art+'/a-z.jpg')
	AddOption('Browse Genres',True, 1220, iconImage=art+'/browsegenres.jpg')
	AddOption('Trakt.TV',True, 1230, iconImage=art+'/trakt.jpg')
	AddOption('IMDB',True, 1240, iconImage=art+'/imdb.jpg')
	AddOption('Search',True, 1250, iconImage=art+'/search.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchMovieAZMenu():
	path = art+'/letters/'
	for character in AZ_DIRECTORIES:
		if character == '#1234': character = '1234'
		icon = path+ urllib.quote_plus(character.lower()+'.jpg')
		AddOption(character,True,1219,character,iconImage=icon)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchMovieGenreMenu():
	DB.connect()
	path = art+'/genres/'
	rows = DB.query("SELECT distinct genre from rw_moviegenres ORDER BY genre ASC")
	for row in rows:
		genre = row[0].lower().replace('-', '')
		if genre in ["japanese", 'none', "talkshow"]: genre = 'genre'
		icon = path+ urllib.quote_plus(genre+'.jpg')
		AddOption(row[0],True,1229, row[0],iconImage=icon)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchMovieTraktMenu():
	AddOption('Trakt.tv Watchlist',True,1239, 'watchlist', 'trakt', iconImage=art+'/traktwatchlist.jpg')
	AddOption('Trakt.tv Trending',True,1239, 'trending', 'trakt', iconImage=art+'/trakttrending.jpg')
	AddOption('Trakt.tv Recommended',True, 1239, 'recommended', 'trakt', iconImage=art+'/traktrecommended.jpg')
	AddOption('Trakt.tv Personal Lists',True, 1239, 'custom', 'trakt', iconImage=art+'/traktpersonallists.jpg')
	AddOption('Trakt.tv Liked Lists',True, 1239, 'liked', 'trakt', iconImage=art+'/traktliked.jpg')
	AddOption('Trakt.tv Popular Lists',True, 1239, 'popular', 'trakt', iconImage=art+'/traktpopular.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def WatchMovieIMDBMenu():
	AddOption('IMDB Watchlist',True,1249, 'watchlist', 'imdb', iconImage=art+'/imdbwatchlist.jpg')
	AddOption('IMDB Top 250',True,1249, 'top250', 'imdb', iconImage=art+'/imdbtop250.jpg')
	AddOption('IMDB MovieMeter',True,1249, 'moviemeter', 'imdb', iconImage=art+'/imdbmoviemeter.jpg')
	AddOption('IMDB Best Picture Winners',True,1249, 'bestpictures', 'imdb', iconImage=art+'/imdbbestpicturewinners.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def ManageMenu():
	AddOption('TV Shows',True, 2100, iconImage=art+'/tvshows.jpg')
	AddOption('Movies',True, 2200, iconImage=art+'/movies.jpg')
	AddOption('Backup Database',False, 2300, iconImage=art+'/backup.jpg')
	AddOption('Restore Database',False, 2400, iconImage=art+'/restore.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def ManageTVMenu():
	AddOption('View TV Subscriptions',True, 2110, iconImage=art+'/watchsubscriptions.jpg')
	AddOption('Subscribe to TV Shows',True, 1100, iconImage=art+'/subscribe.jpg')
	AddOption('Update TV Show Subscriptions',False, 2130, iconImage=art+'/updatesubscriptions.jpg')	
	AddOption('Cache Available TV Shows',False, 2140, iconImage=art+'/cacheavailabletvshows.jpg')	
	AddOption('Delete All Subscriptions',False, 2150, iconImage=art+'/deleteallsubscriptions.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))


def ManageMovieMenu():
	AddOption('Cache Available Movies',False, 2150, iconImage=art+'/cacheavalaiblemovies.jpg')
	AddOption('Add Movies to Library',True, 1200, iconImage=art+'/addmoviestolibrary.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))


def SupportMenu():
	AddOption('View Status',False, 3100, iconImage=art+'/viewstatus.jpg')
	AddOption('FAQ',True, 3200, iconImage=art+'/faq.jpg')
	AddOption('View XMBC.log',False, 3300, iconImage=art+'/log.jpg')
	AddOption('Submit log to xbmclogs',False, 3400, iconImage=art+'/submitlog.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def FAQMenu():
	faq = xbmcpath(rootpath, 'resources/faq.xml')
	file = open(faq, 'r')
	content=file.read()
	file.close()
	soup = BeautifulSoup(content)
	headings = soup.findAll('heading')
	for heading in headings:
		title = heading['title']
		id = heading['id']
		AddOption(title, False, 3210, id, iconImage=art+'/faq.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))


def SettingsMenu():
	AddOption('The Royal We Settings',False, 4100, iconImage=art+'/theroyalwesttings.jpg')
	AddOption('Donnie Settings',False, 4200, iconImage=art+'/donniesettings.jpg')
	AddOption('Service Providers',True, 4300, iconImage=art+'/serviceproviders.jpg')
	AddOption('URLResolver Settings',False, 4400, iconImage=art+'/urlresolversettings.jpg')
	AddOption('Clear Database Lock',False, 4500, iconImage=art+'/cleardatabaselock.jpg')
	AddOption('Install TRW to source.xml',False, 4600, iconImage=art+'/addtrwtosource.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def ProviderMenu():
	log("Listing service providers")
	AddOption("Modify Priorites", True, 4310, iconImage=art+'/serviceproviders.jpg')
	SCR = scrapers.CommonScraper(ADDON_ID, DB, reg)
	for index in range(0, len(SCR.activeScrapers)):
		service = SCR.getScraperByIndex(index).service
		AddOption(SCR.getScraperByIndex(index).name, True, 4320, SCR.getScraperByIndex(index).service, iconImage=art+'/'+service+'.jpg')
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def AvailableProviders(name):
	log("Listing providers by service")
	DB.connect()
	rows = DB.query("SELECT providerid, mirror, enabled FROM rw_providers WHERE provider=? ORDER BY mirror ASC ", [name], force_double_array=True)
	for row in rows:
		try:
			if str2bool(str(row[2])):
				AddOption('[B]'+str(row[1])+'[/B]', False, 4340, str(row[0]))
			else:
				AddOption('[COLOR red]'+str(row[1])+'[/COLOR]', False, 4340, str(row[0]))
		except:
			pass
	xbmcplugin.endOfDirectory(int(sys.argv[1]))

def ListProviders():
	DB.connect()
	rows = DB.query("SELECT provider, mirror, priority, providerid FROM rw_providers ORDER BY priority ASC")
	for row in rows:
		name = "[B]%s.[/B] %s - %s" % (row[2], row[0], row[1])
		key = "%s:%s:%s - %s" % (row[3], row[2], row[0], row[1])
		AddOption(name,False, 4330, key)
	xbmcplugin.endOfDirectory(int(sys.argv[1]))
	
########################
### Params and stuff ###
########################

DEFAULT_CONTEXT = []
cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 4100, '', '')
DEFAULT_CONTEXT.append(('The Royal We Settings', cmd, ''))
cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 4200, '', '')
DEFAULT_CONTEXT.append(('Donnie Settings', cmd, ''))
cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 3100, '', '')
DEFAULT_CONTEXT.append(('View Donnie Status', cmd, '')) 
cmd = 'XBMC.RunPlugin(%s?mode=%s&name=%s&action=%s)' % (sys.argv[0], 4500, '', '')
DEFAULT_CONTEXT.append(('Clear Database Lock', cmd, '')) 

def AddOption(text, isFolder, mode, name='', action='', iconImage="DefaultFolder.png", fanart='', meta=None, contextMenuItems = []):
	global DEFAULT_CONTEXT
	global rootpath
	if fanart=='':
		fanart=rootpath+'/fanart.jpg'
	if meta:
		li = xbmcgui.ListItem(text, iconImage=iconImage)
		li.setInfo(type="Video", infoLabels=meta)
		li.setProperty( "Fanart_Image", fanart )
	else:
		li = xbmcgui.ListItem(text, iconImage=iconImage)
		li.setInfo(type="Video", infoLabels={"Title": text})
		li.setProperty( "Fanart_Image", fanart )
	if contextMenuItems:
		CONTEXT_MENU = contextMenuItems + DEFAULT_CONTEXT
	else:
		CONTEXT_MENU = DEFAULT_CONTEXT 
	if reg.getBoolSetting('fullcontextmenu'):
		replaceItems = False
	else:
		replaceItems = True
	li.addContextMenuItems(CONTEXT_MENU, replaceItems=replaceItems)
	url = sys.argv[0]+'?mode=' + str(mode) + '&name='+  name + '&action='+  action
	return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=isFolder, totalItems=0)

def setView(view):
	if reg.getBoolSetting('enable-default-views'):
		xbmc.executebuiltin("Container.SetViewMode("+view+")")
		xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_UNSORTED )
		xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_LABEL )
		xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RATING )
		xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_DATE )
		xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_PROGRAM_COUNT )
		xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_VIDEO_RUNTIME )
		xbmcplugin.addSortMethod( handle=int( sys.argv[ 1 ] ), sortMethod=xbmcplugin.SORT_METHOD_GENRE )

def GetParams():
	param=[]
	paramstring=sys.argv[len(sys.argv)-1]
	if len(paramstring)>=2:
		cleanedparams=paramstring.replace('?','')
		if (paramstring[len(paramstring)-1]=='/'):
				paramstring=paramstring[0:len(paramstring)-2]
		pairsofparams=cleanedparams.split('&')
		param={}
		for i in range(len(pairsofparams)):
			splitparams={}
			splitparams=pairsofparams[i].split('=')
			if (len(splitparams))==2:
				param[splitparams[0]]=splitparams[1]			
	return param

params=GetParams()
url=None
name=None
mode=None
action=None
path=None
episodeid=None
movieid=None

try:
		url=urllib.unquote_plus(params["url"])
except:
		pass
try:
		name=urllib.unquote_plus(params["name"])
except:
		pass
try:
		episodeid=urllib.unquote_plus(params["episodeid"])
except:
		pass
try:
		movieid=urllib.unquote_plus(params["movieid"])
except:
		pass
try:
		path=urllib.unquote_plus(params["path"])
except:
		pass
try:
		mode=int(params["mode"])
except:
		pass
try:
		action=urllib.unquote_plus(params["action"])
except:
		pass		
log('==========================PARAMS:\ACTION: %s\nNAME: %s\nMODE: %s\nEPISODEID: %s\nMOVIEID: %s\nMYHANDLE: %s\nPARAMS: %s' % ( action, name, mode, episodeid, movieid, sys.argv[1], params ), level=0)


if mode==None: #Main menu
	checkUpgradeStatus()
	AddonMenu()
elif mode==10:
	log('Lanuch Stream')
	LaunchStream(path, episodeid, movieid)
elif mode==20:
	log('Recently Aired')
elif mode==30:
	log('Clear Database Lock')
	ClearDatabaseLock()
elif mode==50:
	log('Watch Stream')
	WatchStream(name, action)
elif mode==60:
	log('Watch Episode')
	WatchEpisode(name, action)
elif mode==70:
	log('Watch url: %s', name)
	WatchURL(name)
elif mode==100:
	log('Autoupdate Subscriptions')
	AutoUpdateSubscriptions()
elif mode==110:
	log('Autoupdate TV Shows')
	AutoUpdateTVShows()
elif mode==120:
	log('Autoupdate Movies')
	AutoUpdateMovies()
elif mode==130:
	log('Update Videolibrary')
	UpateVideoLibrary()
elif mode==140:
	log('Download Artwork')
	DownloadArtwork()
elif mode==150:
	log('Process Queue Item')
	ProcessQueue()

##################### TV ######################################

elif mode==1000:
	log('Watch Menu')
	WatchMenu()
elif mode==1100:
	log('Watch TV Menu')
	WatchTVMenu()

elif mode==1110:
	log('Watch AZ TV Menu')
	WatchTVAZMenu()
elif mode==1119:
	log('Watch AZ TV Results')
	WatchTVResults(name, 'az')

elif mode==1120:
	log('Watch Genre TV Menu')
	WatchTVGenreMenu()
elif mode==1129:
	log('Watch Genre TV Results')
	WatchTVResults(name, 'genre')

elif mode==1130:
	log('Watch Trakt TV Menu')
	WatchTVTraktMenu()
elif mode==1132:
	log('Watch Trakt list: %s, %s', (name,action))
	if name == 'user-custom-list':
		WatchTVTraktResults('list', url=action)
elif mode==1139:
	log('Watch Trakt TV Results')
	WatchTVTraktResults(name)

elif mode==1140:
	log('Watch IMDB TV Menu')
	WatchTVIMDBMenu()
elif mode==1149:
	log('Watch IMDB TV Results')
	WatchTVIMDBResults(name)

elif mode==1150:
	log('Watch TVShow Search')
	search = DoSearch('TV Show Search')
	WatchTVResults(search, 'search')
elif mode==1159:
	log('Watch TVShow Search')
	WatchTVResults(name, 'search')

elif mode==1160:
	log('Watch New TV Episodes')
	WatchTVNewReleases()

elif mode==1170:
	log('Watch Subscriptions')
	WatchTVSubscriptions()

elif mode==1190:
	log('Get Episode List: %s', name)
	GetEpisodeList(name)

##################### MOVIE ###################################

elif mode==1200:
	log('Watch Movie Menu')
	WatchMovieMenu()

elif mode==1210:
	log('Watch AZ Movie Menu')
	WatchMovieAZMenu()
elif mode==1219:
	log('Watch AZ Movie Results')
	WatchMovieResults(name, 'az')

elif mode==1220:
	log('Watch Genre Movie Menu')
	WatchMovieGenreMenu()
elif mode==1229:
	log('Watch Genre Movie Results')
	WatchMovieResults(name, 'genre')

elif mode==1230:
	log('Watch Trakt Movie Menu')
	WatchMovieTraktMenu()
elif mode==1231:
	log('Add movie to Trakt Watchlist')
	addMovieTraktWatch(name)
elif mode==1232:
	log('Watch Trakt list: %s, %s', (name,action))
	if name == 'user-custom-list':
		WatchMovieTraktResults('list', url=action)
	else:
		WatchMovieTraktResults('list', url=name)
elif mode==1233:
	log('Like Trakt list: %s, %s', (name,action))
	TraktLikeList(name, action)

elif mode==1234:
	log('Unlike Trakt list: %s, %s', (name,action))
	TraktUnlikeList(name, action)
elif mode==1235:
	log('Remove movie from Trakt Watchlist')
	removeMovieTraktWatch(name)
elif mode==1236:
	log('Add show to Trakt Watchlist')
	addShowTraktWatch(name)
elif mode==1237:
	log('Remove show from Trakt Watchlist')
	removeShowTraktWatch(name)
elif mode==1239:
	log('Watch Trakt Movie Results')
	WatchMovieTraktResults(name)

elif mode==1240:
	log('Watch IMDB Movie Menu')
	WatchMovieIMDBMenu()
elif mode==1241:
	log('Add movie to IMDB Watchlist')
	addMovieIMDBWatch(name)
elif mode==1242:
	log('Remove movie from IMDB Watchlist')
	removeMovieIMDBWatch(name)
elif mode==1249:
	log('Watch IMDB Movie Results')
	WatchMovieIMDBResults(name)

elif mode==1250:
	log('Watch Movie Search')
	search = DoSearch('Movie Search')
	if search:	
		WatchMovieResults(search, 'search')
elif mode==1259:
	log('Watch Search Movie Results')
	WatchMovieResults(name, 'search')


elif mode==2000:
	log('Manage Menu')
	ManageMenu()
elif mode==2100:
	log('Manage TV Menu')
	ManageTVMenu()
elif mode==2110:
	log('Manage TV Subscriptions')
	ViewTVSubscriptions()
elif mode==2111:
	log('Update TV Subscription')
	UpdateSingleShow(name, action)
elif mode==2112:
	log('Toggle TV Subscription')
	toggleSubscription(name)
elif mode==2113:
	log('Merge TV Subscriptions')
	mergeSubscription(name)
elif mode==2114:
	log('Detelte TV Subscription')
	UnsubscribeShow(name)
elif mode==2115:
	log('Add TV Subscription')
	SubscribeShow(name)


elif mode==2130:
	log('Update TV Subscriptions')
	UpdateTVSubscriptions()
elif mode==2140:
	log('Cache TV List')
	UpdateAvailableTVShows()
elif mode==2150:
	log('Cache Movie List')
	UpdateAvailableMovies()

elif mode==2200:
	log('Manage Movie Menu')
	ManageMovieMenu()

elif mode==2300:
	log('Backup Database')
	BackupDatabase()

elif mode==2400:
	log('Restore Database')
	RestoreDatabase()

elif mode==2500:
	log('Import Movie %s', name)
	ImportMovie(name)

elif mode==3000:
	log('Support Menu')
	SupportMenu()
elif mode==3100:
	log('View Status')
	ViewStatus()
elif mode==3200:
	log('FAQ Menu')
	FAQMenu()
elif mode==3210:
	log('View FAQ')
	ViewFAQ(name)
elif mode==3300:
	log('View Log')
	ViewLOG(show=True)
elif mode==3400:
	log('Submit Log')
	SubmitLog()

elif mode==4000:
	log('Settings Menu')
	SettingsMenu()
elif mode==4100:
	log('TRW Settings')
	selfAddon.openSettings()
elif mode==4200:
	log('Donnie Settings')
	xbmcaddon.Addon(id='script.module.donnie').openSettings()
elif mode==4300:
	log('Settings Menu')
	ProviderMenu()
elif mode==4310:
	log('List Providers')
	ListProviders()
elif mode==4320:
	log('List Providers by: %s', name)
	AvailableProviders(name)
elif mode==4330:
	log('Drag Provider: %s', name)
	DragProvider(name)
elif mode==4340:
	log('Toggle Provider: %s', name)
	ToggleProvider(name)
elif mode==4400:
	log('URLResolver Settings')
	#import urlresolver
	#urlresolver.display_settings()
	xbmcaddon.Addon(id='script.module.urlresolver').openSettings()
elif mode==4500:
	log('Clear Database Lock')
	ClearDatabaseLock()
elif mode==4600:
	log('Update Sources.xml')
	SetupLibrary()




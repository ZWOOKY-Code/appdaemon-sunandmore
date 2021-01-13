"""
	SunAndMore prototype

"""
import appdaemon.plugins.hass.hassapi as hass
import appdaemon.plugins.hass
from datetime import datetime , timedelta , timezone
import threading
import math


class SunAndMore(hass.Hass):

    def initialize(self):
        self.__single_threading_lock = threading.Lock()

        try:
            self._sensor_name = self.args.get('sensor_name', 'sunandmore')
            self._friendly_name = self.args.get('friendly_name', 'SunAndMore')
            self._lat = float(self.args.get('lat', 0))
            self._long = float(self.args.get('long', 0))
            self._tz =  self.args.get('tz', 'Europe/Zurich')
            self._utcoffset = self.args.get('utcoffset', '+1:00')

            self._colortemp_night  = int(self.args.get('colortemp_night', 540 ) )
            self._colortemp_astro  = int(self.args.get('colortemp_astro', 500 ) )
            self._colortemp_nauti  = int(self.args.get('colortemp_nauti', 460 ) )
            self._colortemp_dawn  = int(self.args.get('colortemp_dawn', 390 ) )
            self._colortemp_start  =     self.args.get('colortemp_start', 'dawn' )
            self._colortemp_noon =     self.args.get('colortemp_noon', 180 )
            self._brightness_night = int(self.args.get('brightness_night', 2 ) )
            self._brightness_astro = int(self.args.get('brightness_astro', 5 ) )
            self._brightness_nauti = int(self.args.get('brightness_nauti', 10 ) )
            self._brightness_dawn = int(self.args.get('brightness_dawn', 15 ) )
            self._brightness_start =     self.args.get('brightness_start', 'dawn' )
            self._brightness_dayli =     self.args.get('brigtntess_dayli', 100 )  
            self._brightness_start_v = 0  
            self._brightness         = 255  
            self._brightness_pct = 100


            ## get brightness diff  ONE time calc
            brightness_diff = self._brightness_dayli - self._brightness_dawn
            if   self._brightness_start == 'astro':  # astronomisch
                brightness_diff = self._brightness_dayli - self._brightness_astro
                self._brightness_start_v = self._brightness_astro
            elif self._brightness_start == 'nauti':   # nautical
                brightness_diff = self._brightness_dayli - self._brightness_nauti
                self._brightness_start_v = self._brightness_nauti
            elif self._brightness_start == 'dawn':    # people
                brightness_diff = self._brightness_dayli - self._brightness_dawn
                self._brightness_start_v = self._brightness_dawn
            self._brightness_diff = brightness_diff

            ## get colortemp diff  ONE time calc
            colortemp_diff = self._colortemp_noon - self._colortemp_dawn
            if   self._brightness_start == 'astro':  # astronomisch
                colortemp_diff = self._colortemp_noon - self._colortemp_astro
            elif self._brightness_start == 'nauti':   # nautical
                colortemp_diff = self._colortemp_noon - self._brightness_nauti
            elif self._brightness_start == 'dawn':    # people
                colortemp_diff = self._colortemp_noon - self._colortemp_dawn
            self._colortemp_diff = colortemp_diff


            self._sun_rise         = "01:01"
            self._sun_set          = "01:01"
            self._azimut           = 0
            self._elevation        = 0
            self._elevation_last   = 0
            self._rising           = 0
            self._equation_of_time = 0
            self._sun_declination  = 0
            self._special_text     = ''
            self._icon_template    = 'mdi:sun'

            self._length_of_day_m= 0                # minutes
            self._length_of_day_h= 0                # hours
            self._min_since_rise  = 0
            self._length_of_day    = 0
            self._mired            = 190
            self._kelvin           = 2700

            # sample times for Zurich 7.1.2020
            # Astronomische Nacht:	      00:00 - 06:21        18:43 - 00:00    Gesamt: 11:38
            # Nautische Dämmerung:        06:21 - 06:58        18:06 - 18:43    Gesamt: 01:14
            # Dämmerung:                  06:58 - 07:37        17:27 - 18:06    Gesamt: 01:17
            # Bürgerl. Dämmerung:         07:37 - 08:12        16:52 - 17:27    Gesamt:01:10
            # Tageslicht:                         08:12   -    16:52            Gesamt:08:40
            self._sun_rise_naut       = "06:21"    #  -18 < elevation  < 0  
            self._sun_rise_twil       = "06:58"    #  -12 < elevation  < 0
            self._sun_rise_dawn       = "07:37"    #   -6 < elevation  < 0
            self._sun_rise_dayl       = "08:12"    #    0 < elevation
            self._sun_solnoon         = "13:22"    #        solar noon
            self._sun_set_dawn        = "16:52"    #   -6 < elevation  < 0
            self._sun_set_twil        = "17:27"    #  -12 < elevation  < 0
            self._sun_set_naut        = "18:06"    #  -18 < elevation  < 0
            self._night_start_astr    = "18:43"    #  -18 > elevation
            self._night_end_astr      = "06:21"    #  -18 > elevation
            self._last_calc           = "-"        #  full calculation on a new day
            self._calc_info           = {}


            self._monthList = [
                          {"name": "January",   "numdays": 31, "abbr": "Jan"},
                          {"name": "February",  "numdays": 28, "abbr": "Feb"},
                          {"name": "March",     "numdays": 31, "abbr": "Mar"},
                          {"name": "April",     "numdays": 30, "abbr": "Apr"},
                          {"name": "May",       "numdays": 31, "abbr": "May"},
                          {"name": "June",      "numdays": 30, "abbr": "Jun"},
                          {"name": "July",      "numdays": 31, "abbr": "Jul"},
                          {"name": "August",    "numdays": 31, "abbr": "Aug"},
                          {"name": "September", "numdays": 30, "abbr": "Sep"},
                          {"name": "October",   "numdays": 31, "abbr": "Oct"},
                          {"name": "November",  "numdays": 30, "abbr": "Nov"},
                          {"name": "December",  "numdays": 31, "abbr": "Dec"},
                          ]
             
            self._SunTimes = [
                          {  'sunrise'      : -0.833  }
                        , {  'sunset'       : -0.833 }
                        , {  'sunriseEnd'   : -0.3 }
                        , {  'sunriseEnd'   : -0.3 }
                        , {  'dawn'         : -6  }
                        , {  'dusk'         : -6  }
                        , {  'nauticalDawn' : -12  }
                        , {  'nauticalDusk' : -12  }
                        , {  'nightEnd'     : -18  }
                        , {  'night'        : -18  }
                        , {  'goldenHourEnd': 6  }
                        , {  'goldenHour'   : 6  }
                            ]
                            
        except (TypeError, ValueError):
            # self.log("Invalid Configuration", level="ERROR")
            return

        # self.log("----------------------------------------------------------------", level="INFO")
        # self.log("--", level="INFO")
        # self.log("-- SunAndMore", level="INFO")
        # self.log("--", level="INFO")
        # self.log("----------------------------------------------------------------", level="INFO")
        
        self._sam_timer = self.run_in(self.sam_timer_callback, 1  ) ## immediat call for initializing everything



    def sam_timer_callback(self,  kwargs):
        # self.log("sam callback " )

        # self.EasyCalc()                          ## easy version
        curr_time = datetime.now()               ## GMT  python version
        # curr_time = self.datetime(True)          ## Appdaemon Local Date and Time / Param be aware of TZ
        utc_offset = self.get_tz_offset()        ##        

        delta = self.get_min_from_HM( self._utcoffset )
        delta = delta - 60  #  correction 
        if delta < 0:
            delta =abs(delta)
            curr_time = datetime.now() - timedelta(minutes=delta)
        else:
            curr_time = datetime.now() + timedelta(minutes=delta)
       
        
        data = {
              "year" : curr_time.year 	                                                  ##
            , "month" : curr_time.month                                                   ##
            , "day" : curr_time.day                                                       ##
            , "hour" : curr_time.hour                                                     ##
            , "minute" : curr_time.minute                                                 ##
            , "second" : curr_time.second                                                 ##
            , "time_local" : curr_time.hour*60 + curr_time.minute + curr_time.second/60   ##   date['hour']*60 + date['minute'] + date['second']/60.0
            , "utc_offset" : self._utcoffset.split(":")                                   ## +/- TZ
            , "lat" : self._lat                                                           ##
            , "lon" : self._long                                                          ##
         #    , "tz" : float(self._utcoffset.split(":")[0]) + float(self._utcoffset.split(":")[1])/60.0                                                             ## Europe/Zurich
            , "tz" : float(self._utcoffset.split(":")[0]) + float(self._utcoffset.split(":")[1])/60.0                                                             ## Europe/Zurich
            }

            
        # self.log('############# data: {}' . format(data) )

        self.calculate( data , False )                                                  ## NOAA Version
        
        restart = 58-datetime.now().second
        if restart <=0:
        	restart = 58
        self._sam_timer = self.run_in(self.sam_timer_callback, restart   )



    ###  NOAA CALC  ####################################################################


    ###  NOAA CALC  ####################################################################
    ###  NOAA CALC  ####################################################################
    ###  NOAA CALC  ####################################################################
    ###  NOAA CALC  ####################################################################
    ###  based on:  https://www.esrl.noaa.gov/gmd/grad/solcalc/calcdetails.html
    # /*************************************************************/
    # /* Solar position calculation functions */
    # /*************************************************************/
    def calculate(self,data , adjusttz):       
        # data = self.get_input_data(adjusttz)
        # self.log('#############222 data: {}' . format(data) )
        
        jday = self.getJD(data['year'], data['month'], data['day'] )
        total = jday + data['time_local']/1440.0 - data['tz']/24.0
        T = self.calcTimeJulianCent(total)
        azel = self.calcAzEl(T, data['time_local'] , data['lat'], data['lon'], data['tz'])
        eqTime = self.calcEquationOfTime(T)
        theta  = self.calcSunDeclination(T)
        self._equation_of_time = round(eqTime,2 )
        self._sun_declination = round(theta,2)
        
        if jday != self._last_calc:
            self._last_calc = jday
            solnoon = self.calcSolNoon(jday, data['lon'], data['tz'])

            sun_rise = self.calcSunriseSet(1, jday, data['lat'], data['lon'], data['tz'] , -0.833)
            sun_set  = self.calcSunriseSet(0, jday, data['lat'], data['lon'], data['tz'] , -0.833)
            sun_rise_end = self.calcSunriseSet(1, jday, data['lat'], data['lon'], data['tz'] , -0.3) 
            sun_set_start  = self.calcSunriseSet(0, jday, data['lat'], data['lon'], data['tz'] , -0.3)

            blue_rise_s = self.calcSunriseSet(1, jday, data['lat'], data['lon'], data['tz'] , -8 )
            blue_rise_e = self.calcSunriseSet(1, jday, data['lat'], data['lon'], data['tz'] , -4 )
            blue_set_s = self.calcSunriseSet(0, jday, data['lat'], data['lon'], data['tz'] , -4 )
            blue_set_e = self.calcSunriseSet(0, jday, data['lat'], data['lon'], data['tz'] , -8 )

            gold_rise_s = self.calcSunriseSet(1, jday, data['lat'], data['lon'], data['tz'] , 10 )
            gold_rise_e = self.calcSunriseSet(1, jday, data['lat'], data['lon'], data['tz'] , 12 )
            gold_set_s = self.calcSunriseSet(0, jday, data['lat'], data['lon'], data['tz'] , 12 )
            gold_set_e = self.calcSunriseSet(0, jday, data['lat'], data['lon'], data['tz'] , 10 )


            dawn_rise = self.calcSunriseSet(1, jday, data['lat'], data['lon'], data['tz'] , -6 )
            dawn_set  = self.calcSunriseSet(0, jday, data['lat'], data['lon'], data['tz'] , -6 )
            naut_rise = self.calcSunriseSet(1, jday, data['lat'], data['lon'], data['tz'] , -12 )
            naut_set  = self.calcSunriseSet(0, jday, data['lat'], data['lon'], data['tz'] , -12 )
            astr_rise = self.calcSunriseSet(1, jday, data['lat'], data['lon'], data['tz'] , -18 )
            astr_set  = self.calcSunriseSet(0, jday, data['lat'], data['lon'], data['tz'] , -18 )

            self._sun_solnoon = self.timeString(solnoon,2 )

            self._sun_rise = self.dateTimeFormat( sun_rise , jday )
            self._sun_set = self.dateTimeFormat( sun_set , jday )
            self._sun_rise_end = self.dateTimeFormat( sun_rise_end , jday )
            self._sun_set_start = self.dateTimeFormat( sun_set_start , jday )
            self._dawn_rise = self.dateTimeFormat( dawn_rise , jday )
            self._dawn_set = self.dateTimeFormat( dawn_set , jday )
            self._naut_rise = self.dateTimeFormat( naut_rise , jday )
            self._naut_set = self.dateTimeFormat( naut_set , jday )
            self._astr_rise = self.dateTimeFormat( astr_rise , jday )
            self._astr_set = self.dateTimeFormat( astr_set , jday )

            self._blue_rise_s = self.dateTimeFormat( blue_rise_s , jday )
            self._blue_rise_e = self.dateTimeFormat( blue_rise_e , jday )
            self._blue_set_s = self.dateTimeFormat( blue_set_s , jday )
            self._blue_set_e = self.dateTimeFormat( blue_set_e , jday )

            self._gold_rise_s = self.dateTimeFormat( gold_rise_s , jday )
            self._gold_rise_e = self.dateTimeFormat( gold_rise_e , jday )
            self._gold_set_s = self.dateTimeFormat( gold_set_s , jday )
            self._gold_set_e = self.dateTimeFormat( gold_set_e , jday )

            daylength_m =0
            daylength_h =0
            if self._brightness_start == 'astro':
                daylength_m = ((self.get_min_from_HM(self._astr_set)-self.get_min_from_HM(self._astr_rise)) )
                daylength_h = ((self.get_hours_from_HM(self._astr_set)-self.get_hours_from_HM(self._astr_rise)) )
            elif self._brightness_start == 'nauti':
                daylength_m = ((self.get_min_from_HM(self._naut_set)-self.get_min_from_HM(self._naut_rise)) )
                daylength_h = ((self.get_hours_from_HM(self._naut_set)-self.get_hours_from_HM(self._naut_rise)) )
            elif self._brightness_start == 'dawn':
                daylength_m = ((self.get_min_from_HM(self._dawn_set)-self.get_min_from_HM(self._dawn_rise)) )
                daylength_h = ((self.get_hours_from_HM(self._dawn_set)-self.get_hours_from_HM(self._dawn_rise)) )
            elif self._brightness_start == 'rise':
                daylength_m = ((self.get_min_from_HM(self._sun_set)-self.get_min_from_HM(self._sun_rise)) )
                daylength_h = ((self.get_hours_from_HM(self._sun_set)-self.get_hours_from_HM(self._sun_rise)) )
            else:
                daylength_m = ((self.get_min_from_HM(self._sun_set)-self.get_min_from_HM(self._sun_rise)) )
                daylength_h = ((self.get_hours_from_HM(self._sun_set)-self.get_hours_from_HM(self._sun_rise)) )
            self._length_of_day_m = round(daylength_m,4)
            self._length_of_day_h = round(daylength_h,4)
            # self.log('day  m:{} h:{} {} - {}'.format(daylength_m,daylength_h ,self._astr_set , self._astr_rise) )

            #this is needed to calculate the mired starting info .....

            solardepression = -0.8331
            #  solardepression = 0
            jday_first    = self.getDayInfoFor( data['year'],  3, 21  ,data , solardepression)                  #  frühling day north
            jday_longest  = self.getDayInfoFor( data['year'],  6, 21  ,data , solardepression)                  #  longest day north
            jday_third    = self.getDayInfoFor( data['year'],  9, 21  ,data , solardepression)                  #  herbst day north
            jday_shortest = self.getDayInfoFor( data['year'], 12, 21  ,data , solardepression)                  #  shortest day north
            dl_f = 0
            dl_l = 0
            dl_t = 0
            dl_s = 0
            if self._lat < 0: #  south
                jday_first    = self.getDayInfoFor( data['year'],  3, 21  ,data , solardepression)                  #  frühling day north
                jday_longest  = self.getDayInfoFor( data['year'],  12, 21  ,data , solardepression)                 #  shortest day SOUTH !!!!!!!!!!!
                jday_third    = self.getDayInfoFor( data['year'],  9, 21  ,data , solardepression)                  #  herbst day north
                jday_shortest = self.getDayInfoFor( data['year'], 6, 21  ,data , solardepression)                   #  longest day SOUTH !!!!!!!!!!!!

            # self.log('jday_s: f:{} l:{} t:{} s:{} '.format(jday_first,jday_longest,jday_third,jday_shortest ) )
            dl_f = round( ((self.get_hours_from_HM( jday_first['set'])   - self.get_hours_from_HM( jday_first['rise']    ))) ,2)
            dl_l = round( ((self.get_hours_from_HM( jday_shortest['set'])- self.get_hours_from_HM( jday_shortest['rise'] ))) ,2)
            dl_t = round( ((self.get_hours_from_HM( jday_third['set'])   - self.get_hours_from_HM( jday_third['rise']    ))) ,2)
            dl_s = round( ((self.get_hours_from_HM( jday_longest['set']) - self.get_hours_from_HM( jday_longest['rise']  ))) ,2)

            # self.log('dlfs: f:{} l:{} t:{} s:{} '.format(jday_first,jday_longest,jday_third,jday_shortest ) )
                      
            self._calc_info = {  
                                       'dl_f' : dl_f
                                     , 'dl_l' : dl_l
                                     , 'dl_t' : dl_t
                                     , 'dl_s' : dl_s
                            
                            ,  'day' : {
                                              'shortest' :  round((self.get_hours_from_HM( jday_shortest['set'])- self.get_hours_from_HM( jday_shortest['rise'])),2)
                                            , 'first'    :  round((self.get_hours_from_HM( jday_first['set'])   - self.get_hours_from_HM( jday_first['rise'])),2)
                                            , 'longest'  :  round((self.get_hours_from_HM( jday_longest['set']) - self.get_hours_from_HM( jday_longest['rise'])),2) 
                                            , 'third'    :  round((self.get_hours_from_HM( jday_third['set'])   - self.get_hours_from_HM( jday_third['rise'])),2)
                                           }
                             , 'azimut_s': {
                                             'shortest'  : jday_shortest['azimut_s']
                                           , 'first'     : jday_first['azimut_s']
                                           , 'longest'   : jday_longest['azimut_s']
                                           , 'third'     : jday_third['azimut_s']
                                            }         
                             , 'azimut_m': {
                                             'shortest'  : jday_shortest['azimut_m']
                                           , 'first'     : jday_first['azimut_m']
                                           , 'longest'   : jday_longest['azimut_m']
                                           , 'third'     : jday_third['azimut_m']
                                            }         
                             , 'azimut_e': {
                                             'shortest'  : jday_shortest['azimut_e']
                                           , 'first'     : jday_first['azimut_e']
                                           , 'longest'   : jday_longest['azimut_e']
                                           , 'third'     : jday_third['azimut_e']
                                            }         
                          , 'elevation_s': {
                                             'shortest'  : jday_shortest['elevation_s']
                                           , 'first'     : jday_first['elevation_s']
                                           , 'longest'   : jday_longest['elevation_s']
                                           , 'third'     : jday_third['elevation_s']
                                            }         
                          , 'elevation_m': {
                                             'shortest'  : jday_shortest['elevation_m']
                                           , 'first'     : jday_first['elevation_m']
                                           , 'longest'   : jday_longest['elevation_m']
                                           , 'third'     : jday_third['elevation_m']
                                            }         
                          , 'elevation_e': {
                                             'shortest'  : jday_shortest['elevation_e']
                                           , 'first'     : jday_first['elevation_e']
                                           , 'longest'   : jday_longest['elevation_e']
                                           , 'third'     : jday_third['elevation_e']
                                            }         
                                    }
            
            # objective_s =  p_objective_s       # 0.005                              # -> produce approximately 340 mired at  sunrise/sunset
            # objective_w =  p_objective_w       # 0.030                              # -> produce approximately 340 mired at  sunrise/sunset
            # x_GE_0      =  p_x_GE_0            # 0.075                              # -> change this value until you have obtained the right "edge" mired value above
            
            # self.log('Calcinfo: {}'.format( self._calc_info ) )
            # a = self.MiredCalc( 500, 180 , self._length_of_day_m , data['time_local'] )
            # self.log('MiredCalc: {}'.format(a) )
            # dumy = 1/0
            
            # a = self.MiredCalc_wrong( 500, 180 , 0.030 , 0.005 , 0.075  );
            
            # self.log('MiredCalc: {}'.format(a) )
            
            # noch im IF Statement
        # END OF IF statement

     
        # self.log('calcinfo:{}'.format( self._calc_info ) )
        

        # // azimuth and elevation boxes, azimuth line
        solarZen = 90.0 - azel['elevation']
        self._azimut     = math.floor(azel['azimuth']*100 + 0.5)/100.0
        self._elevation  = math.floor(azel['elevation']*100 + 0.5)/100.0
        if solarZen > 108.0:
            self._special_text = 'dark'
        else:
            self._azimut     = math.floor(azel['azimuth']*100 + 0.5)/100.0
            self._elevation  = math.floor(azel['elevation']*100 + 0.5)/100.0
            self._special_text = ''


        # self.log('UTC offset:  {}'.format( self._utcoffset  ) )
        # self.log('sun_rise:    {}'.format( self._sun_rise  ) )
        # self.log('sun_set:     {}'.format( self._sun_set  ) )
        # self.log('solnoon:     {}'.format( self._sun_solnoon  ) )
        # self.log('azimut:      {}'.format( self._azimut  ) )
        # self.log('elevation:   {}'.format( self._elevation  ) )
        # self.log('declination: {}'.format( self._sun_declination  ) )
        # self.log('eq of time:  {}'.format( self._equation_of_time  ) )
        # self.log('special text:{}'.format( self._special_text  ) )

        # rising state ###################################################################
        if self._elevation_last != self._elevation:
            if self._elevation > self._elevation_last:
                self._rising =1
            else:
            	self._rising =0
            self._elevation_last = self._elevation	
        
        # icon ###########################################################################
        self._icon_template    = 'mdi:sun'
        if self._elevation <= -12:
        	self._icon_template    = 'mdi:weather-night'
        elif self._elevation <= -6:
        	if self._rising == 1:
        	    self._icon_template    = 'mdi:weather-sunset-up'
        	else:
        	    self._icon_template    = 'mdi:weather-sunset-down'
        else:
        	self._icon_template    = 'mdi:sun'

        # min since rise based on start of day
        min_since_rise =0
        if self._rising == 1 and 0==1:  # this is USELESS here !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            if self._brightness_start == 'astro' and self._elevation >= -18:
                min_since_rise = ( data['hour']*60+data['minute'] ) -  self.get_min_from_HM(self._astr_rise)
            if self._brightness_start == 'nauti' and self._elevation >= -12:
                min_since_rise = ( data['hour']*60+data['minute'] ) -  self.get_min_from_HM(self._naut_rise)
            if self._brightness_start == 'dawn' and self._elevation >= -6:
                min_since_rise = ( data['hour']*60+data['minute'] ) -  self.get_min_from_HM(self._dawn_rise)
            if self._brightness_start == 'rise' and self._elevation >= - 0.833:
                min_since_rise = ( data['hour']*60+data['minute'] ) -  self.get_min_from_HM(self._sun_rise)
            self._min_since_rise = min_since_rise

        # special times during day
        day_light_2 = ''
        if self._elevation >= 10 and self._elevation <= 12 :
            day_light_2 = 'Golden hour'
        elif self._elevation >= -4 and self._elevation <= -8 :
            day_light_2 = 'Blue hour'
        self._day_light_2 = day_light_2

        # times during day
        day_light_1 = 'Night'
        if self._elevation >= -0.3:
            day_light_1 = 'Day'
        elif self._elevation >= -0.8333:
            day_light_1 = 'Sunrise'
        elif self._elevation >= -6:
            day_light_1 = 'Civil dawn'
        elif self._elevation >= -12:
            day_light_1 ='Nautical dawn'
        elif self._elevation >= -18:
            day_light_1 ='Astronomical dawn'
        self._day_light_1 = day_light_1
   

        # self.log( '############## {}\n min_since_rise: ########## {} ' .format( self.datetime(True) , min_since_rise  ) )
        
        # length_of_day ##########################################################################
        min_since_rise = 0
        if self._brightness_start == 'astro' and self._elevation >= -18:
            min_since_rise = ((self.get_min_from_HM(self._astr_set)-self.get_min_from_HM(self._astr_rise)) )
        if self._brightness_start == 'nauti' and self._elevation >= -12:
            min_since_rise = ( data['hour']*60+data['minute'] ) -  self.get_min_from_HM(self._naut_rise)
        if self._brightness_start == 'dawn' and self._elevation >= -6:
            min_since_rise = ( data['hour']*60+data['minute'] ) -  self.get_min_from_HM(self._dawn_rise)
        if self._brightness_start == 'rise' and self._elevation >= - 0.833:
            min_since_rise = ( data['hour']*60+data['minute'] ) -  self.get_min_from_HM(self._sun_rise)
        self._min_since_rise = min_since_rise
 

        # this is for mired calculation 
        daylength = 0.0000001
        if self._brightness_start == 'astro' and self._elevation >= -18:
            daylength = ((self.get_sec_from_HM(self._astr_set)-self.get_sec_from_HM(self._astr_rise)) / 3600)
            daylength = (daylength*-0.0063616)+0.11131
        if self._brightness_start == 'nauti' and self._elevation >= -12:
            daylength = ((self.get_sec_from_HM(self._naut_set)-self.get_sec_from_HM(self._naut_rise)) / 3600)
            daylength = (daylength*-0.0063616)+0.11131
        if self._brightness_start == 'dawn' and self._elevation >= -6:
            daylength = ((self.get_sec_from_HM(self._dawn_set)-self.get_sec_from_HM(self._dawn_rise)) / 3600)
            daylength = (daylength*-0.0063616)+0.11131
        if self._brightness_start == 'rise' and self._elevation >= - 0.833:
            daylength = ((self.get_sec_from_HM(self._sun_set)-self.get_sec_from_HM(self._sun_rise)) / 3600)
            daylength = (daylength*-0.0063616)+0.11131
        self._length_of_day = daylength


        ## ###############################################################################
        ## mired/kelvin Brightness calculation ###########################################
        ## ###############################################################################

        col_default = self._colortemp_night
        if self._elevation >= -18:
            col_default = self._colortemp_astro
        if self._elevation >= -12:
            col_default = self._colortemp_nauti
        if self._elevation >= -6:
            col_default = self._colortemp_dawn
        if self._elevation >= - 0.833:
            col_default = self._colortemp_noon

        col_offset  = self._colortemp_night
        if self._elevation < -18:
            col_offset  = self._colortemp_night
        elif self._colortemp_start == 'astro' and self._elevation >= -18:
            col_offset = self._colortemp_astro
        elif self._colortemp_start == 'nauti' and self._elevation >= -12:
            col_offset = self._colortemp_nauti
        elif self._colortemp_start == 'dawn' and self._elevation >= -6:
            col_offset = self._colortemp_dawn
        elif self._colortemp_start == 'rise' and self._elevation >= - 0.833:
            col_offset = self._colortemp_noon
        else:
            col_offset = self._colortemp_noon

        brightness_default = self._brightness_night
        if self._elevation >= -18:
            brightness_default = self._brightness_astro
        if self._elevation >= -12:
            brightness_default = self._brightness_nauti
        if self._elevation >= -6:
            brightness_default = self._brightness_dawn
        if self._elevation >= - 0.833:
            brightness_default = self._brightness_dayli

        brightness_offset  = self._brightness_night
        if self._elevation < -18:
            brightness_offset  = self._brightness_night
        elif self._brightness_start == 'astro' and self._elevation >= -18:
            brightness_offset = self._brightness_astro
        elif self._brightness_start == 'nauti' and self._elevation >= -12:
            brightness_offset = self._brightness_nauti
        elif self._brightness_start == 'dawn' and self._elevation >= -6:
            brightness_offset = self._brightness_dawn
        elif self._brightness_start == 'rise' and self._elevation >= - 0.833:
            brightness_offset = self._brightness_dayli
        else:
            brightness_offset = self._brightness_dayli

        
        # col_mired  = 0
        # col_kelvin = 0
        # if col_default < 1000:
        #     col_mired  = col_default
        #     col_kelvin = 1000000 / col_mired
        # else:
        #     col_kelvin = col_default
        #     col_mired = 1000000 / col_kelvin
        # self.log('WHAT:  off:{} dai:{} sinc:{}' . format(col_offset, self._colortemp_noon ,self._min_since_rise ) )
        if col_default != self._colortemp_night and self._min_since_rise > 0 :
            everything = self.CircadianCalc( col_offset , self._colortemp_noon , self._length_of_day_m , self._min_since_rise )
            col_mired  = everything['current']['mired']
            col_kelvin = everything['current']['kelvin']
            self._mired   = col_mired
            self._kelvin  = col_kelvin
        else:
            if col_default < 1000:
                col_mired  = int( col_default )
                col_kelvin = int(1000000 / col_mired)        
                self._mired   = col_mired
                self._kelvin  = col_kelvin
            else:
                col_kelvin  = int( col_default )
                col_mired = int(1000000 / col_kelvin)        
                self._mired   = col_mired
                self._kelvin  = col_kelvin

        # self.log('####1 - A')
        if brightness_default != self._brightness_night and self._min_since_rise > 0 :
            # self.log('####1 - B')
            everything     = self.Brightness_Calc( brightness_offset , self._brightness_dayli , self._length_of_day_m , self._min_since_rise )
            brightness     = everything['current']['brightness']
            brightness_pct = everything['current']['brightness_pct']
            self._brightness     = brightness
            self._brightness_pct = brightness_pct
        else:
            # self.log('####1 - C')
            if self._brightness_dayli <= 100:
                # self.log('####1 - D')
                brightness_pct     = int( brightness_default )
                brightness         = int( brightness_pct /100 * 255 )        
                self._brightness     = brightness
                self._brightness_pct = brightness_pct
            else:
                # self.log('####1 - E')
                brightness           = int( brightness_default )
                brightness_pct       = int( brightness /255 * 100 )        
                self._brightness     = brightness
                self._brightness_pct = brightness_pct



          # round ((round( self._length_of_day , 5 ) * (( self._azimut - 180 )**180 + 175)),0)         
          # {{ ((states.sensor.length_of_day_factor.state | round (5))*((states.sun.sun.attributes.azimuth)-180)**2 + 175) | int }}
                  
        self.set_state("sensor."+self._sensor_name+"_mired"
		                            , state =              self._mired, 
		                               attributes = { 
                                      "friendly_name" : self._friendly_name + ' mired'  
                              , "unit_of_measurement" : 'mired'
                                                     })
        self.set_state("sensor."+self._sensor_name+"_kelvin"
		                            , state =              self._kelvin, 
		                               attributes = { 
                                      "friendly_name" : self._friendly_name + ' kelvin' 
                              , "unit_of_measurement" : 'kelvin'
                                                     })
        self.set_state("sensor."+self._sensor_name+"_brightness"
		                            , state =              self._brightness, 
		                               attributes = { 
                                      "friendly_name" : self._friendly_name + ' brightness' 
                              , "unit_of_measurement" : 'brightness'
                                                     })

        self.set_state("sensor."+self._sensor_name+"_brightness_pct"
		                            , state =              self._brightness_pct, 
		                               attributes = { 
                                      "friendly_name" : self._friendly_name + ' brightness pct' 
                              , "unit_of_measurement" : 'brightness_pct'
                                                     })
                                                 
        self.set_state("sensor."+self._sensor_name 
		                            , state =              self._elevation, 
		                               attributes = { 
                                      "friendly_name" :    self._friendly_name + ' info' 
		                            , "elevation":         self._elevation 
		                            , "azimut":            self._azimut 
		                            , "declination":       self._sun_declination 
		                            , "equation_of_time":  self._equation_of_time 
		                            , "rising":            self._rising 
		                            , "localtime":         str(data['hour'])+':'+str(data['minute'])
                                    , "min_since_rise":    self._min_since_rise
		                            , "twillight":         self._day_light_1 
		                            , "special time":      self._day_light_2 
		                            , "special_text":      self._special_text 

		                            , "mired":             self._mired
		                            , "kelvin":            self._kelvin
		                            , "brightness":        self._brightness
		                            , "brightness_pct":    self._brightness_pct
		                         
		                            , "astro_rise":        self._astr_rise                # -18
		                            , "nauti_rise":        self._naut_rise                # -12
		                            , "blue_rise_s":       self._blue_rise_s              # -8
		                            , "dawn_rise":         self._dawn_rise                # -6
		                            , "blue_rise_e":       self._blue_rise_e              # -4
		                            , "sun_rise":          self._sun_rise                 # -0.833
		                            , "sun_rise_end":      self._sun_rise_end             # -0.3
		                            , "gold_rise_s":       self._gold_rise_s              # 10
		                            , "gold_rise_e":       self._gold_rise_e              # 12
		                            , "sun_noon":          self._sun_solnoon              # high
		                            , "gold_set_s":        self._gold_set_s               # 10
		                            , "gold_set_e":        self._gold_set_e               # 12
		                            , "sun_set_start":     self._sun_set_start            # -0.3
		                            , "sun_set":           self._sun_set                  # -0.833
		                            , "blue_set_s":        self._blue_set_s               # -4
		                            , "dawn_set":          self._dawn_set                 # -6
		                            , "blue_set_e":        self._blue_set_e               # -8
		                            , "naut_set":          self._naut_set                 # -12
		                            , "astr_set":          self._astr_set                 # -18

       
		                            , "icon_template":       self._icon_template 
		                            , "length_of_day":       self._length_of_day
                                    , "length_of_day_min":   self._length_of_day_m
                                    , "length_of_day_hours": self._length_of_day_h
		                            , "unit_of_measurement" : 'elevation'
		                              })


        # // sunrise line
        # if ($('#showsr').prop('checked')) {
        # if (rise.azimuth >= 0.0) {
        # showLineGeodesic2("sunrise", "#00aa00", rise.azimuth, data['lat'], data['lon']);
        # }
        # }
 

        # // sunset line
        # if ($('#showss').prop('checked')) {
        # if (set.azimuth >= 0.0) {
        # showLineGeodesic2("sunset", "#ff0000", set.azimuth, data['lat'], data['lon']);
        # }


    ## ###############################################################################
    ## Brightness calculation ########################################################
    ## ###############################################################################
    def Brightness_Calc(self , p_val_rise , p_val_noon , p_daylength , p_curr_minute  ):
        # self.log('VALS p_val_rise:{} p_val_noon:{} p_daylength:{} p_curr_minute:{}  '.format(  p_val_rise , p_val_noon , p_daylength , p_curr_minute  ) )

        daylength       =  0                                                 # in minutes
        daylength_2     =  0                                                 # halber Tag
        daylength_sqrt  =  0                                                 # wurzel
        dayfactor_diff  =  0
        val_s = 0
        val_m = 0
        val_e = 0
        val_c = 0
        base = 'brightness'
        kelvin_s  =  0
        kelvin_m  =  0
        kelvin_e  =  0
        kelvin_c  =  0
        mired_s   =  0
        mired_m   =  0
        mired_e   =  0
        mired_c   =  0
 
        if p_val_noon > 255:                       # Max value
            p_val_noon = 255

        if p_val_noon <= 100:                       # Max value
            p_val_noon = int( p_val_noon / 100 * 255 )
            p_val_rise = int( p_val_rise / 100 * 255 )
            

            
        if 1 == 1:  # this is KELVIN formula
            base = 'brightness'
            val_noon  =  p_val_noon                # 6500                          # 6'500 kelvin = 153 mired
            val_rise  =  p_val_rise                # 2700                          # 2'700 kelvin = 350 mired 2'000 = 500
            val_diff  =  val_noon - val_rise       # 2800                          # 2'700 kelvin = 350 mired 2'000 = 500
          
            daylength       =  p_daylength                                        # in minutes
            daylength_2     =  daylength / 2                                      # halber Tag
            daylength_sqrt  =  math.sqrt( daylength_2 )                           # wurzel
            dayfactor_diff  =  val_diff / (daylength_2**2)
            # self.log('VALS2 val_rise:{} val_noon:{} val_diff:{} daylength:{} df:{} p_curr_minute:{}  '.format(  val_rise , val_noon, val_diff , daylength ,dayfactor_diff, p_curr_minute  ) )

            val_s         = val_noon - ( ( ( ( (-1) * daylength_2) + 0             )**2 ) * dayfactor_diff  ) 
            val_m         = val_noon - ( ( ( ( (-1) * daylength_2) + daylength_2   )**2 ) * dayfactor_diff  ) 
            val_e         = val_noon - ( ( ( ( (-1) * daylength_2) + daylength     )**2 ) * dayfactor_diff  )         
            val_c         = val_noon - ( ( ( ( (-1) * daylength_2) + p_curr_minute )**2 ) * dayfactor_diff  )         
            brgtne_s       =  int( val_s )
            brgtne_m       =  int( val_m )
            brgtne_e       =  int( val_e )
            brgtne_c       =  int( val_c )
            brgtne_pct_s   =  int( brgtne_s / 255 * 100 )
            brgtne_pct_m   =  int( brgtne_m / 255 * 100 )
            brgtne_pct_e   =  int( brgtne_e / 255 * 100 )
            brgtne_pct_c   =  int( brgtne_c / 255 * 100 )
            # self.log('brightness dl:{} dl2:{} dl_sq:{} dayf:{} \ns:{} m:{} e:{} c:{} \nval_noon:{} val_rise:{} val_diff:{} '.format( daylength, daylength_2, daylength_sqrt, dayfactor_diff , val_s, val_m, val_e,val_c,val_noon,val_rise ,val_diff ) )


        ret = {  
                 'brightness' :   {  's' : brgtne_s
                                  ,  'm' : brgtne_m
                                  ,  'e' : brgtne_e
                                  }
               , 'kelvin':   {  's' : brgtne_pct_s
                             ,  'm' : brgtne_pct_m
                             ,  'e' : brgtne_pct_e
                             }
               ,   'day' :   {  'length'         : daylength
                             ,  'length_2'       : daylength_2
                             ,  'length_sqrt'    : daylength_sqrt
                             ,  'factor'         : dayfactor_diff
                             ,  'current_min'    : p_curr_minute
                             }
               ,'current' :  {  'brightness'     : brgtne_c  
                             ,  'brightness_pct' : brgtne_pct_c
                             }
              }
        # self.log('########## ret: {}' . format(ret) )
        # dmumy = 1/0
        return ret
 

    ## ###############################################################################
    ## Circadian calculation #########################################################
    ## ###############################################################################
    def CircadianCalc(self , p_val_rise , p_val_noon , p_daylength , p_curr_minute  ):
        self.log('VALS p_val_rise:{} p_val_noon:{} p_daylength:{} p_curr_minute:{}  '.format(  p_val_rise , p_val_noon , p_daylength , p_curr_minute  ) )

        
#        if p_val_noon >1000:                                                  # we need to calculate based on mired 
#            val_noon  =  1000000/p_val_noon  # kelvin in mired
#            val_rise  =  1000000/p_val_rise  # 350 / 500                      # 2'700 kelvin = 350 mired 2'000 = 500
#            val_diff  =  val_rise - val_noon # 350 / 500                      # 2'700 kelvin = 350 mired 2'000 = 500

        daylength       =  0                                                 # in minutes
        daylength_2     =  0                                                 # halber Tag
        daylength_sqrt  =  0                                                 # wurzel
        dayfactor_diff  =  0
        val_s = 0
        val_m = 0
        val_e = 0
        val_c = 0
        base = 'mired'
        kelvin_s  =  0
        kelvin_m  =  0
        kelvin_e  =  0
        kelvin_c  =  0
        mired_s   =  0
        mired_m   =  0
        mired_e   =  0
        mired_c   =  0

        if  p_val_noon <= 1000:  # this is mired formula
            base = 'mired'
            val_noon  =  p_val_noon                # 190                          # 6'500 kelvin = 153 mired
            val_rise  =  p_val_rise                # 350 / 500                    # 2'700 kelvin = 350 mired 2'000 = 500
            val_diff  =  val_rise - val_noon       # 350 / 500                    # 2'700 kelvin = 350 mired 2'000 = 500
            daylength       =  p_daylength                                        # in minutes
            daylength_2     =  daylength / 2                                      # halber Tag
            daylength_sqrt  =  math.sqrt( daylength_2 )                           # wurzel
            dayfactor_diff  =  val_diff / (daylength_2**2)

            val_s         = val_noon + ( ( ( ( (-1) * daylength_2) + 0             )**2 ) * dayfactor_diff  ) 
            val_m         = val_noon + ( ( ( ( (-1) * daylength_2) + daylength_2   )**2 ) * dayfactor_diff  ) 
            val_e         = val_noon + ( ( ( ( (-1) * daylength_2) + daylength     )**2 ) * dayfactor_diff  )         
            val_c         = val_noon + ( ( ( ( (-1) * daylength_2) + p_curr_minute )**2 ) * dayfactor_diff  )         
            kelvin_s  =  int(1000000 / val_s )
            kelvin_m  =  int(1000000 / val_m )
            kelvin_e  =  int(1000000 / val_e )
            kelvin_c  =  int(1000000 / val_c )
            mired_s   =  int( val_s )
            mired_m   =  int( val_m )
            mired_e   =  int( val_e )
            mired_c   =  int( val_c )
            self.log('mired dl:{} dl2:{} dl_sq:{} dayf:{} s:{} m:{} e:{} '.format( daylength, daylength_2, daylength_sqrt, dayfactor_diff , val_s, val_m, val_e ) )
 
        if p_val_noon >1000:  # this is KELVIN formula
            base = 'kelvin'
            val_noon  =  p_val_noon                # 6500                          # 6'500 kelvin = 153 mired
            val_rise  =  p_val_rise                # 2700                          # 2'700 kelvin = 350 mired 2'000 = 500
            val_diff  =  val_noon - val_rise       # 2800                          # 2'700 kelvin = 350 mired 2'000 = 500
          
            daylength       =  p_daylength                                        # in minutes
            daylength_2     =  daylength / 2                                      # halber Tag
            daylength_sqrt  =  math.sqrt( daylength_2 )                           # wurzel
            dayfactor_diff  =  val_diff / (daylength_2**2)
            # self.log('VALS2 val_rise:{} val_noon:{} val_diff:{} daylength:{} df:{} p_curr_minute:{}  '.format(  val_rise , val_noon, val_diff , daylength ,dayfactor_diff, p_curr_minute  ) )

            val_s         = val_noon - ( ( ( ( (-1) * daylength_2) + 0             )**2 ) * dayfactor_diff  ) 
            val_m         = val_noon - ( ( ( ( (-1) * daylength_2) + daylength_2   )**2 ) * dayfactor_diff  ) 
            val_e         = val_noon - ( ( ( ( (-1) * daylength_2) + daylength     )**2 ) * dayfactor_diff  )         
            val_c         = val_noon - ( ( ( ( (-1) * daylength_2) + p_curr_minute )**2 ) * dayfactor_diff  )         
            kelvin_s  =  int(val_s )
            kelvin_m  =  int(val_m )
            kelvin_e  =  int(val_e )
            kelvin_c  =  int(val_c )
            mired_s   =  int(1000000 / val_s )
            mired_m   =  int(1000000 / val_m )
            mired_e   =  int(1000000 / val_e )
            mired_c   =  int(1000000 / val_c )
            self.log('KELVIN dl:{} dl2:{} dl_sq:{} dayf:{} \ns:{} m:{} e:{} c:{} \nval_noon:{} val_rise:{} val_diff:{} '.format( daylength, daylength_2, daylength_sqrt, dayfactor_diff , val_s, val_m, val_e,val_c,val_noon,val_rise ,val_diff ) )


        ret = {  
                 'mired' :   {  's' : mired_s
                             ,  'm' : mired_m
                             ,  'e' : mired_e
                             }
               , 'kelvin':   {  's' : kelvin_s
                             ,  'm' : kelvin_m
                             ,  'e' : kelvin_e
                             }
               ,   'day' :   {  'length'      : daylength
                             ,  'length_2'    : daylength_2
                             ,  'length_sqrt' : daylength_sqrt
                             ,  'factor'      : dayfactor_diff
                             ,  'current_min' : p_curr_minute
                             }
               ,   'base' :  {  'noon'  : val_noon
                             ,  'rise'  : val_rise
                             ,  'diff'  : val_diff
                             }
               ,'current' :  {  'base'        : base  
                             ,  'mired'       : mired_c
                             ,  'kelvin'      : kelvin_c
                             }
              }
        # self.log('########## ret: {}' . format(ret) )
        # dmumy = 1/0
        return ret
                               
                               
    def CircadianCalc_wrong(self , p_mired_rise , p_mired_noon , p_objective_w , p_objective_s , p_x_GE_0  ):
        mired_noon  =  p_mired_noon        # 190                                # 6'500 kelvin = 153 mired
        mired_rise  =  p_mired_rise        # 350                                # 2'700 kelvin = 350 mired
                                                                                # 2'000 kelvin = 500 mired
        objective_w =  p_objective_w       # 0.030                              # -> produce approximately 340 mired at  sunrise/sunset
        objective_s =  p_objective_s       # 0.005                              # -> produce approximately 340 mired at  sunrise/sunset

        x_GE_0      =  p_x_GE_0            # 0.075                              # -> change this value until you have obtained the right "edge" mired value above

        daylength_w =  self._calc_info['dl_s']                                  # in hours
        daylength_s =  self._calc_info['dl_l']                                  # in hours

        # self.log('objective_w:{} objective_s:{} daylength_s:{} daylength_w:{}'.format ( objective_w , objective_s , daylength_s  , daylength_w) )
        
        # growth      =  -( objective_w - objective_s ) / ( daylength_s - daylength_w )
        if daylength_s - daylength_w <=0:
            growth      =  -( objective_w - objective_s ) / ( 4 )  # tagesdifferenz für gegenden die zuweit noerdlich oder suedlich sind
        else:
            growth      =  -( objective_w - objective_s ) / ( daylength_s - daylength_w )

        azimut_s_s = self._calc_info['azimut_s']['longest']
        azimut_m_s = self._calc_info['azimut_m']['longest']
        azimut_e_s = self._calc_info['azimut_e']['longest']

        azimut_s_w = self._calc_info['azimut_s']['shortest']
        azimut_m_w = self._calc_info['azimut_m']['shortest']
        azimut_e_w = self._calc_info['azimut_e']['shortest']

        factor_u_s  =  ( daylength_s * growth )+ x_GE_0
        factor_u_w  =  ( daylength_w * growth )+ x_GE_0
        
        mired_s_s   = ( factor_u_s * ( azimut_s_s - 180 )**2 ) + mired_noon
        mired_m_s   = ( factor_u_s * ( azimut_m_s - 180 )**2 ) + mired_noon
        mired_e_s   = ( factor_u_s * ( azimut_e_s - 180 )**2 ) + mired_noon
        
        mired_s_w   = ( factor_u_w * ( azimut_s_w - 180 )**2 ) + mired_noon
        mired_m_w   = ( factor_u_w * ( azimut_m_w - 180 )**2 ) + mired_noon
        mired_e_w   = ( factor_u_w * ( azimut_e_w - 180 )**2 ) + mired_noon
        
        # allInONE = (( daylength_s * -( objective_w - objective_s ) / ( daylength_s - daylength_w ) )+ x_GE_0 * ( azimut_s_s - 180 )^2 ) + 190
        # allInONE = (( 15.8 * -( 0.030 - 0.005 ) / ( 15.8 - 8.5 ) )+ 0.075 * ( x - 180 )^2 ) + 190
        # allInONE = (( 15.8 * -( 0.025 ) / ( 7.3 ) )+ 0.075 * ( x - 180 )^2 ) + 190

        ret =  {   
                   'summer' : { 's': mired_s_s
                              , 'm': mired_m_s
                              , 'e': mired_e_s
                               }
                 , 'winter' : { 's': mired_s_w
                              , 'm': mired_m_w
                              , 'e': mired_e_w
                               }
                 , 'growth'        : growth
                 , 'factor_u_s'    : factor_u_s
                 , 'factor_u_w'    : factor_u_w
               }
        return ret
        
    
    def getDayInfoFor(self , y,m,d ,data ,solardepression ):
        data['year'] = y
        data['month'] = m
        data['day'] = d
        jday = self.getJD(data['year'], data['month'], data['day'] )
        solnoon = self.calcSolNoon(jday, data['lon'], data['tz'])
        sol_h = self.timeString(solnoon,2 ).split(':')[0]
        sol_m = self.timeString(solnoon,2 ).split(':')[1]
        # self.log('sol H:{} m:{}'.format(sol_h , sol_m) )
        loc_start = self.calcSunriseSet(1, jday, data['lat'], data['lon'], data['tz'] , solardepression  )
        loc_end   = self.calcSunriseSet(0, jday, data['lat'], data['lon'], data['tz'] , solardepression  )
        # self.log('############# data:{} \nstart:{} jday{} \loc_start:{} \loc_end:{}'.format(data,loc_start,jday,loc_start,loc_end ) )

        loc_time_local = self.get_min_from_HM( self.dateTimeFormat(loc_start, jday) )
        total = jday + loc_time_local /1440.0 - data['tz']/24.0
        T = self.calcTimeJulianCent(total)
        # self.log('####T start :{}'.format(T) )
        loc_azel_start = self.calcAzEl(T, loc_time_local , data['lat'], data['lon'], data['tz'])
        loc_start_azimut     = math.floor(loc_azel_start['azimuth']*100 + 0.5)/100.0
        loc_start_elevation  = math.floor(loc_azel_start['elevation']*100 + 0.5)/100.0
            
        loc_time_local = self.get_min_from_HM( self.dateTimeFormat(loc_end, jday) )
        total = jday + loc_time_local/1440.0 - data['tz']/24.0
        T = self.calcTimeJulianCent(total)
        # self.log('####T end :{}'.format(T) )
        loc_azel_end = self.calcAzEl(T, loc_time_local , data['lat'], data['lon'], data['tz'])
        loc_end_azimut     = math.floor(loc_azel_end['azimuth']*100 + 0.5)/100.0
        loc_end_elevation  = math.floor(loc_azel_end['elevation']*100 + 0.5)/100.0

        loc_time_local = int(sol_h)*60 + int(sol_m)
        total = jday + loc_time_local/1440.0 - data['tz']/24.0
        T = self.calcTimeJulianCent(total)
        # self.log('####T noon :{}'.format(T) )
        loc_azel_max = self.calcAzEl(T, loc_time_local , data['lat'], data['lon'], data['tz'])
        loc_max_azimut     = math.floor(loc_azel_max['azimuth']*100 + 0.5)/100.0
        loc_max_elevation  = math.floor(loc_azel_max['elevation']*100 + 0.5)/100.0
        
        data = {
                     "azimut_s": loc_start_azimut 
                   , "azimut_m": loc_max_azimut 
                   , "azimut_e": loc_end_azimut
                   , "elevation_s": loc_start_elevation 
                   , "elevation_m": loc_max_elevation 
                   , "elevation_e": loc_end_elevation
                   , "rise":   self.dateTimeFormat( loc_start , jday )
                   , "noon":   self.timeString(solnoon,2 )
                   , "set":   self.dateTimeFormat( loc_end , jday )
                    }
        return data

    #                       800          50            80
    def calcBrightness(self,total_steps,current_step, brightness_diff ):
        full_after = 8

        if total_steps ==0 or current_step ==0: 
            return 0
        
        steps_start_end = total_steps / full_after        # 100
        # self.log('steps_start_end:{} total_steps:{}'.format ( steps_start_end , total_steps ,   ) )
        
        if current_step > 0:
            brightness_to_full = brightness_diff / steps_start_end * current_step
        else:
            if steps_start_end - current_step <= steps_start_end:
                brightness_to_full = brightness_diff / steps_start_end * ( total_steps/2 - current_step ) * (-1)
            else:
                brightness_to_full = brightness_diff

        if brightness_to_full > brightness_diff:
            brightness_to_full = brightness_diff
            
        if brightness_to_full < 0:
            brightness_to_full = 0

        # self.log('steps_start_end:{} total_steps:{} brightness_to_full:{} '.format ( steps_start_end , total_steps ,  brightness_to_full ) )
        
        return brightness_to_full

    def dateTimeFormat(self,my_check,jday):
        my_ret=''
        if my_check['jday'] == jday:
            my_ret = self.timeString(my_check['timelocal'],2)
        else:
            if my_check['azimuth'] >=0.0:
                my_ret = self.timeDateString(my_check['jday'], my_check['timelocal'] )
            else:
                my_ret = self.dayString(my_check['jday'],0,3)
        return my_ret
                
    def get_sec_from_HM(self,time_str):
        # get seconds from H:M:
        if self.isTime(time_str) == True:
            h, m = time_str.split(':')
            return int(h) * 3600 + int(m) * 60
        return 0

    def get_min_from_HM(self,time_str):
        # get seconds from H:M:
        if self.isTime(time_str) == True:
            h, m = time_str.split(':')
            return int(h) * 60 + int(m)
        return 0

    def get_hours_from_HM(self,time_str):
        # get seconds from H:M:
        # self.log('str:{} ' . format(time_str )   )
        if self.isTime(time_str) == True:
            h, m = time_str.split(':')
            ret = round( (int(h) + (int(m)/60*100)/100) , 2)
            return ret
        return 0
    
    def get_input_data(self,adjusttz):
        date = self.getDatevals()
        mins = date['hour']*60 + date['minute'] + date['second']/60.0
        lat = float( self._lat )
        lng = float( self._long )
        tzname = 'Europe/Zurich';

        # // get utc offset for selected timezone and date
        # if (adjusttz == false) {
        # utcoffset = $('#zonebox').val()
        # 
        # } else {
        # // make sure utc offset is set correctly
        # // (may have changed entered day value if it was out of range)
        # var datestr = getDateString(date)
        # var utcoffset = moment(datestr).tz(tzname).format('Z');
        # $('#zonebox').val(utcoffset)
        # }

        my_utcoffset= "+1:00"
        utcoffset = my_utcoffset.split(":")
        tz = float(utcoffset[0]) + float(utcoffset[1])/60.0

        data = {
            "year": date['year'], 
            "month": date['month'],
            "day": date['day'],
            "hour": date['hour'],
            "minute": date['minute'],
            "second": date['second'],
            "time_local": mins,
            "utc_offset": utcoffset,
            "lat": lat,
            "lon": lng,
            "tz": tz,
            }
        return data




    # //--------------------------------------------------------------
    # // returns a string in the form DDMMMYYYY[ next] to display prev/next rise/set
    # // flag=2 for DD MMM, 3 for DD MM YYYY, 4 for DDMMYYYY next/prev
    def dayString(self,jd, neXt, flag):
        if jd < 900000 or jd > 2817000:
            return  "error 1"

        date = self.calcDateFromJD(jd)
        # self.log('############## date: {}'.format(date) )
        output =''
        if flag == 2:
            # self.log('############ flag 2 ')
            output = self.zeroPad(date['day'],2) + " " + self._monthList[date['month']-1]['abbr']
        if flag == 3:
            # self.log('############ flag 3 m:{} d:{} y:{}' . format(date['month'],date['day'], str(date['year']) )  )
            # self.log('############ flag 3 mo:{} ' . format ( self._monthList[date['month']-1]['abbr']  ) )
            output = self.zeroPad(date['day'],2) + self._monthList[date['month']-1]['abbr'] + str(date['year'])
            # self.log('############ flag 3 out:{} date:{}' . format ( output  , self.zeroPad(date['day'],2) )  )
        if flag == 4:
            # self.log('############ flag 4 ')
            output = self.zeroPad(date['day'],2) + self._monthList[date['month']-1]['abbr'] + str(date['year'])
            if neXt == True:
                output = output + " next"
            else:
                output = output + " prev"
            
        return output



    # //--------------------------------------------------------------
    def timeDateString(self,JD, minutes):
        return timeString(minutes, 2) + " " + dayString(JD, 0, 2)

    # //--------------------------------------------------------------
    # // timeString returns a zero-padded string (HH:MM:SS) given time in minutes
    # // flag=2 for HH:MM, 3 for HH:MM:SS
    def timeString(self,minutes, flag):
        if minutes >= 0 and minutes < 1440:
            floatHour = minutes / 60.0
            hour = math.floor(floatHour)
            floatMinute = 60.0 * (floatHour - math.floor(floatHour))
            minute = math.floor(floatMinute)
            floatSec = 60.0 * (floatMinute - math.floor(floatMinute))
            second = math.floor(floatSec + 0.5)
            if second > 59:
                second = 0
                minute += 1
            if flag == 2 and second >= 30:
                # minute +=1  # original
                minute = minute +1
            if minute > 59:
                minute = 0
                hour += 1
            output = self.zeroPad(hour,2) + ":" + self.zeroPad(minute,2)
            if flag > 2:
                output = output + ":" + self.zeroPad(second,2)
        else:
            output = "error 2"

        return output


    #// get, validate, reset if necessary, the date and time input boxes
    def getDatevals(self):
        # docmonth = $('#mosbox').prop('selectedIndex') + 1
        # docday = $('#daybox').prop('selectedIndex') + 1
        # docyear = readTextBox("yearbox", 5, 1, 0, -2000, 3000, 2009)
        # dochr = readTextBox("hrbox", 2, 1, 1, 0, 23, 12)
        # docmn = readTextBox("mnbox", 2, 1, 1, 0, 59, 0)
        # docsc = readTextBox("scbox", 2, 1, 1, 0, 59, 0)

        docmonth = 1
        docday = 6
        docyear = 2021
        dochr = 11
        docmn = 00
        docsc = 11

        if self.isLeapYear(docyear) and docmonth == 2:
            if docday > 29:
                docday = 29
                # $('#daybox').prop('selectedIndex', docday - 1)
        else:
            #if  docday > monthList[docmonth-1].numdays:
            #    docday = monthList[docmonth-1].numdays
            if docmonth in [1,3,5,7,8,10,12] and docday > 31:
                docday = 31
            elif docmonth in [2,4,6,9,11] and docday > 30:
                docday = 30

        return {"year": docyear, "month": docmonth, "day": docday, "hour": dochr, "minute": docmn, "second": docsc}

    def getDateString(self,date):
        s = date['year']
        + '-' 
        + self.zeroPad(date['month'],2) 
        + '-' 
        + self.zeroPad(date['day'],2) 
        + 'T' 
        + self.zeroPad(date['hour'],2) 
        + ':' 
        + self.zeroPad(date['minute'],2) 
        + ':'
        + self.zeroPad(date['second'],2)
        return s

    def zeroPad(self,n, digits):
        n = str(n)
        while len(n) < digits:
            n = '0' + n;
        return n;


    def calcTimeJulianCent(self,jd):
        T = (jd - 2451545.0)/36525.0
        return T
    
    def calcJDFromJulianCent(self,t):
        JD = t * 36525.0 + 2451545.0
        return JD
    
    def isLeapYear(self,yr):
        leapyear = ((yr % 4 == 0 and yr % 100 != 0) or yr % 400 == 0)
        return leapyear
    
    def calcDateFromJD(self,jd):
        z = math.floor(jd + 0.5)
        f = (jd + 0.5) - z
        if (z < 2299161):
            A = z
        else:
            alpha = math.floor((z - 1867216.25)/36524.25)
            A = z + 1 + alpha - math.floor(alpha/4)
        B = A + 1524
        C = math.floor((B - 122.1)/365.25)
        D = math.floor(365.25 * C)
        E = math.floor((B - D)/30.6001)
        day = int(B - D - math.floor(30.6001 * E) + f)
        month = 0
        if E < 14:
            month = E-1
        else:
            month = E-13
        year = 0
        if month > 2:
            year = C - 4716
        else:
            year = C - 4715
        return {"year": year, "month": month, "day": day}
    
    def calcDoyFromJD(self,jd):
        date = self.calcDateFromJD(jd)
        k = 0
        if self.isLeapYear(date['year'] ):
            k=1
        else:
            k=2
        doy = math.floor((275 * date['month'])/9) - k * math.floor((date['month'] + 9)/12) + date['day'] -30
        return doy
    
    def radToDeg(self,angleRad):
    	return (180.0 * angleRad / math.pi);
    
    def degToRad(self,angleDeg):
    	return (math.pi * angleDeg / 180.0)
    
    def calcGeomMeanLongSun(self,t):
    	L0 = 280.46646 + t * (36000.76983 + t*(0.0003032))
    	while L0 > 360.0:
    		L0 -= 360.0
    	while L0 < 0.0:
    		L0 += 360.0
    	return L0		# in degrees
    
    def calcGeomMeanAnomalySun(self,t):
    	M = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    	return M		# in degrees
    
    def calcEccentricityEarthOrbit(self,t):
    	e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    	return e		# unitless
    
    def calcSunEqOfCenter(self,t):
    	m = self.calcGeomMeanAnomalySun(t)
    	mrad = self.degToRad(m)
    	sinm = math.sin(mrad)
    	sin2m = math.sin(mrad+mrad)
    	sin3m = math.sin(mrad+mrad+mrad)
    	C = sinm * (1.914602 - t * (0.004817 + 0.000014 * t)) + sin2m * (0.019993 - 0.000101 * t) + sin3m * 0.000289
    	return C		# in degrees
    
    def calcSunTrueLong(self,t):
    	l0 = self.calcGeomMeanLongSun(t)
    	c = self.calcSunEqOfCenter(t)
    	O = l0 + c
    	return O		# in degrees
    
    def calcSunTrueAnomaly(self,t):
    	m = self.calcGeomMeanAnomalySun(t)
    	c = self.calcSunEqOfCenter(t)
    	v = m + c
    	return v		# in degrees
    
    def calcSunRadVector(self,t):
    	v = self.calcSunTrueAnomaly(t)
    	e = self.calcEccentricityEarthOrbit(t)
    	R = (1.000001018 * (1 - e * e)) / (1 + e * math.cos(self.degToRad(v)))
    	return R		# in AUs
    
    def calcSunApparentLong(self,t):
        o = self.calcSunTrueLong(t)
        omega = 125.04 - 1934.136 * t
        lam = o - 0.00569 - (0.00478 * math.sin(self.degToRad(omega)))
        return lam		# in degrees
    
    
    def calcMeanObliquityOfEcliptic(self,t):
    	seconds = 21.448 - t*(46.8150 + t*(0.00059 - t*(0.001813)))
    	e0 = 23.0 + (26.0 + (seconds/60.0))/60.0
    	return e0		# in degrees
    
    def calcObliquityCorrection(self,t):
    	e0 = self.calcMeanObliquityOfEcliptic(t)
    	omega = 125.04 - 1934.136 * t
    	e = e0 + 0.00256 * math.cos(self.degToRad(omega))
    	return e		# in degrees
    
    def calcSunRtAscension(self,t):
    	e = self.calcObliquityCorrection(t)
    	lam = self.calcSunApparentLong(t)
    	tananum = (math.cos(self.degToRad(e)) * math.sin(self.degToRad(lam)))
    	tanadenom = (math.cos(self.degToRad(lam)))
    	alpha = self.radToDeg(math.atan2(tananum, tanadenom))
    	return alpha		# in degrees
    
    def calcSunDeclination(self,t):
    	e = self.calcObliquityCorrection(t)
    	lam = self.calcSunApparentLong(t)
    	sint = math.sin(self.degToRad(e)) * math.sin(self.degToRad(lam))
    	theta = self.radToDeg(math.asin(sint))
    	return theta		# in degrees
    
    def calcEquationOfTime(self,t):
    	epsilon = self.calcObliquityCorrection(t)
    	l0 = self.calcGeomMeanLongSun(t)
    	e = self.calcEccentricityEarthOrbit(t)
    	m = self.calcGeomMeanAnomalySun(t)
    	y = math.tan(self.degToRad(epsilon)/2.0)
    	y *= y
    	sin2l0 = math.sin(2.0 * self.degToRad(l0))
    	sinm   = math.sin(self.degToRad(m))
    	cos2l0 = math.cos(2.0 * self.degToRad(l0))
    	sin4l0 = math.sin(4.0 * self.degToRad(l0))
    	sin2m  = math.sin(2.0 * self.degToRad(m))
    	Etime = y * sin2l0 - 2.0 * e * sinm + 4.0 * e * y * sinm * cos2l0 - 0.5 * y * y * sin4l0 - 1.25 * e * e * sin2m
    	return self.radToDeg(Etime)*4.0	# in minutes of time


    def calcHourAngleSunrise(self,lat, solarDec,solardepression):
    	latRad = self.degToRad(lat)
    	sdRad  = self.degToRad(solarDec)
    	HAarg = (math.cos(self.degToRad(90.0 + ( -1 * solardepression) ))/(math.cos(latRad)*math.cos(sdRad))-math.tan(latRad) * math.tan(sdRad))
    	# HA = math.acos(HAarg)   ## original
    	HA = 0
    	# self.log('############# HAarg {}' .format(HAarg) )
    	if  HAarg >= -1 and HAarg <= 1:
    	    HA = math.acos(HAarg)
    	else:
    	    HA = 'NaN'
    	# self.log('############# HA {}' .format(HA) )
    	return HA		# in radians (for sunset, use -HA)
    
    def isTime(self,inputVal):
        oneDecimal = False
        inputStr = "" + str(inputVal)
        for i in range( len(inputStr) ):
            oneChar = inputStr[ i ]
            if i == 0 and (oneChar == "-" or oneChar == "+"):
                continue
            if oneChar == ":" and oneDecimal == False:
                oneDecimal = True
                continue
            if oneChar < "0" or oneChar > "9":
                return False
        return True

    def isNumber(self,inputVal):
    	oneDecimal = False
    	inputStr = "" + str(inputVal)
    	for i in range( len(inputStr) ):
    		oneChar = inputStr[ i ]
    		if i == 0 and (oneChar == "-" or oneChar == "+"):
    			continue
    		if oneChar == "." and oneDecimal == False:
    			oneDecimal = True
    			continue
    		if oneChar < "0" or oneChar > "9":
    			return False
    	return True
    
    def getJD(self,year, month, day):
        if month <= 2:
            year -= 1
            month += 12
    	
        A = math.floor(year/100)
        B = 2 - A + math.floor(A/4)
        JD = math.floor(365.25*(year + 4716)) + math.floor(30.6001*(month+1)) + day + B - 1524.5
        return JD
    
    def calcRefraction(self,elev):
    
    	if elev > 85.0:
    		correction = 0.0
    	else:
    		te = math.tan(self.degToRad(elev))
    		if elev > 5.0:
    			correction = 58.1 / te - 0.07 / (te*te*te) + 0.000086 / (te*te*te*te*te)
    		elif elev > -0.575:
    			correction = 1735.0 + elev * (-518.2 + elev * (103.4 + elev * (-12.79 + elev * 0.711) ) )
    		else:
    			correction = -20.774 / te
    		correction = correction / 3600.0
    	return correction
    
    def calcAzEl(self,T, localtime, latitude, longitude, zone):
    	eqTime = self.calcEquationOfTime(T)
    	theta  = self.calcSunDeclination(T)
    	solarTimeFix = eqTime + 4.0 * longitude - 60.0 * zone
    	earthRadVec = self.calcSunRadVector(T)
    	trueSolarTime = localtime + solarTimeFix
    	while trueSolarTime > 1440:
    		trueSolarTime -= 1440
    	hourAngle = trueSolarTime / 4.0 - 180.0
    	if  hourAngle < -180:
    		hourAngle += 360.0
    	haRad = self.degToRad(hourAngle)
    	csz = math.sin(self.degToRad(latitude)) * math.sin(self.degToRad(theta)) + math.cos(self.degToRad(latitude)) * math.cos(self.degToRad(theta)) * math.cos(haRad)
    	if csz > 1.0:
    		csz = 1.0
    	elif csz < -1.0: 
    		csz = -1.0
    	zenith = self.radToDeg(math.acos(csz))
    	azDenom = ( math.cos(self.degToRad(latitude)) * math.sin(self.degToRad(zenith)))
    	if abs(azDenom) > 0.001:
    		azRad = (( math.sin(self.degToRad(latitude)) * math.cos(self.degToRad(zenith)) ) - math.sin(self.degToRad(theta))) / azDenom
    		if abs(azRad) > 1.0:
    			if azRad < 0:
    				azRad = -1.0
    			else:
    				azRad = 1.0
    		azimuth = 180.0 - self.radToDeg(math.acos(azRad))
    		if hourAngle > 0.0:
    			azimuth = -azimuth
    	else:
    		if latitude > 0.0:
    			azimuth = 180.0
    		else:
    			azimuth = 0.0
    	if azimuth < 0.0:
    		azimuth += 360.0
    	exoatmElevation = 90.0 - zenith
    	# Atmospheric Refraction correction
    	refractionCorrection = self.calcRefraction(exoatmElevation)
    	solarZen = zenith - refractionCorrection
    	elevation = 90.0 - solarZen
    	return {"azimuth": azimuth, "elevation": elevation}
    
    def calcSolNoon(self,jd, longitude, timezone):
    	tnoon = self.calcTimeJulianCent(jd - longitude/360.0)
    	eqTime = self.calcEquationOfTime(tnoon)
    	solNoonOffset = 720.0 - (longitude * 4) - eqTime # in minutes
    	newt = self.calcTimeJulianCent(jd + solNoonOffset/1440.0)
    	eqTime = self.calcEquationOfTime(newt)
    	solNoonLocal = 720 - (longitude * 4) - eqTime + (timezone*60.0) # in minutes
    	while solNoonLocal < 0.0:
    		solNoonLocal += 1440.0
    	while solNoonLocal >= 1440.0:
    		solNoonLocal -= 1440.0
    	return solNoonLocal
    

    
    def calcSunriseSetUTC(self,rise, JD, latitude, longitude,solardepression):
    	t = self.calcTimeJulianCent(JD)
    	eqTime = self.calcEquationOfTime(t)
    	solarDec = self.calcSunDeclination(t)
    	hourAngle = self.calcHourAngleSunrise(latitude, solarDec,solardepression)
    	if hourAngle == 'NaN':
    	    return 'NaN'
    	if rise == 0:
    	    hourAngle = hourAngle * -1
    	delta = longitude + self.radToDeg(hourAngle)
    	timeUTC = 720 - (4.0 * delta) - eqTime	# in minutes
    	# self.log('calcSunRiseSet:: eqTime:{} solarDec:{} hourAngle:{} delta:{} longitude:{} timeUTC: {}'.format (eqTime, solarDec, hourAngle, delta,longitude, timeUTC ) )
    	return timeUTC

    
    # rise = 1 for sunrise, 0 for sunset
    def calcSunriseSet(self,rise, JD, latitude, longitude, timezone,solardepression):
    
        timeUTC = self.calcSunriseSetUTC(rise, JD, latitude, longitude,solardepression)
        NoSunRise = 0
        if self.isNumber(timeUTC) == False:
            # self.log('##############1 timeUTC: {}'.format(timeUTC) )
            dummy = 1
            NoSunRise = 1
        else:
            newTimeUTC = self.calcSunriseSetUTC(rise, JD + timeUTC/1440.0, latitude, longitude,solardepression) 
            # self.log('##############1 newTimeUTC: {}'.format(newTimeUTC) )
            # self.log('####################: rise: {}'.format (rise) )
            if self.isNumber(newTimeUTC):
                NoSunRise = 0
                timeLocal = newTimeUTC + (timezone * 60.0)
                riseT = self.calcTimeJulianCent(JD + newTimeUTC/1440.0)
                riseAzEl = self.calcAzEl(riseT, timeLocal, latitude, longitude, timezone)
                azimuth = riseAzEl['azimuth']
                # self.log('####################: riseT: {} azimuth:{}'.format ( riseT , azimuth ) )
                jday = JD
                if timeLocal < 0.0 or timeLocal >= 1440.0:
                    increment = 0
                    if timeLocal < 0:
                        increment = 1
                    else:
                        increment = -1
    
                    while timeLocal < 0.0 or timeLocal >= 1440.0:
                        timeLocal = timeLocal + increment * 1440.0
                        jday = jday - increment
            else:
                NoSunRise = 1 
        if NoSunRise == 1: # no sunrise/set found
            azimuth = -1.0
            timeLocal = 0.0
            doy = self.calcDoyFromJD(JD)
            # self.log('##############1 lat:{} doy:{}'.format( latitude, doy) )

            if (( latitude > 66.4 and doy > 79 and doy < 267 ) 
            or ( latitude < -66.4 and ( doy < 83  or  doy > 263 ))):
                # previous sunrise/next sunset
                # self.log('####################: rise: {}'.format (rise) )
                nrise =1
                if rise == 1:
                    nrise = 0
                else:
                    nrise = 1
                jday = self.calcJDofNextPrevRiseSet(nrise, rise, JD, latitude, longitude, timezone,solardepression)
            else:   # previous sunset/next sunrise
                jday = self.calcJDofNextPrevRiseSet(rise, rise, JD, latitude, longitude, timezone,solardepression)
                # self.log('####################222222: jday: {}'.format ( jday ) )
                
        return {"jday": jday, "timelocal": timeLocal, "azimuth": azimuth}


    def calcJDofNextPrevRiseSet(self,neXt, rise, JD, latitude, longitude, tz,solardepression):
    	julianday = JD
    	inCrement = 0
    	if neXt ==1:
    	    inCrement = 1.0
    	else:
    	    inCrement = -1.0
    	time = self.calcSunriseSetUTC(rise, julianday, latitude, longitude,solardepression)
    	while self.isNumber(time) == False:
    		julianday += inCrement
    		time = self.calcSunriseSetUTC(rise, julianday, latitude, longitude,solardepression)
    	timeLocal = time + tz * 60.0
    	while timeLocal < 0.0 or timeLocal >= 1440.0:
    		incr = 0
    		if timeLocal < 0:
    		    incr = 1
    		else:
    		    -1
    		timeLocal += (incr * 1440.0)
    		julianday -= incr
    	return julianday    
    #/*************************************************************/
    #/* end calculation functions */
    #/*************************************************************/

    ###  EASYCALC  ####################################################################
    ###  EASYCALC  ####################################################################
    ###  EASYCALC  ####################################################################
    ###  EASYCALC  ####################################################################
    ## based on http://www.geoastro.de/SME/tk/index.htm
    def EasyCalc(self):
        ## nothing defined yet
        
        lat = 47.43995
        long = 8.437788
        month = 6
        day = 1
        hour = 12
        minute = 0
        
        KeqPi180 = 0.017453
        day_count = (month-1)*30.3+day
        year_piece = (day_count-1+((hour+minute/60)-12)/24)/365
        declination = ( 0.006918-0.399912*math.cos( 2*math.pi * year_piece) + 0.070257 * math.sin( 2*math.pi*year_piece)-0.006758*math.cos(2*year_piece*math.pi ) )
        declination = (0.006918-0.399912*math.cos(2*math.pi*year_piece)+0.070257*math.sin(2*math.pi*year_piece)-0.006758*math.cos(2*year_piece*math.pi)+0.000907*math.sin(2*year_piece*math.pi)-0.002697*math.cos(3*year_piece*math.pi)+0.00148*math.sin(3*year_piece*math.pi))/KeqPi180
        time_equal = 229.18*(0.000075+0.001868*math.cos(2*math.pi*year_piece)-0.032077*math.sin(2*math.pi*year_piece)-0.014615*math.cos(2*2*math.pi*year_piece)-0.040849*math.sin(2*2*math.pi*year_piece))
        hour_rad =(hour*60+minute+time_equal+4*long-60)/4-180
        sun_height_sin = math.sin(KeqPi180*lat)*math.sin(KeqPi180*declination)+math.cos(KeqPi180*lat)*math.cos(KeqPi180*declination)*math.cos(KeqPi180*hour_rad)
        sun_height = math.asin(sun_height_sin)/KeqPi180
        azimut_cos = -(math.sin(KeqPi180*lat)*sun_height_sin-math.sin(KeqPi180*declination))/(math.cos(KeqPi180*lat)*math.sin(math.acos(sun_height_sin)))
        azimut = 0
        if hour+minute/60 <= 12+(15-long)/15-time_equal/60:
            azimut = math.acos(azimut_cos)/KeqPi180
        else:
            azimut = 360-math.acos(azimut_cos)/KeqPi180
    


    ###  COLOR STUFF  ####################################################################
    ###  COLOR STUFF  ####################################################################
    ###  COLOR STUFF  ####################################################################
    ###  COLOR STUFF  ####################################################################
    def convert_KELVIN_to_MIRED(self, kelvin ):
        # A mired is a microreciprocal degree. It’s derived by dividing 1,000,000 by the Kelvin temperature. So 5600K has a mired of 180 (1,000,000/5600 = 179.57).
        mired = int(1000000/int(kelvin))
        return mired
        
    def convert_MIRED_to_KELVIN(self, mired ):
        kelvin = int(1000000/int(mired))
        return kelvin

    def convert_KELVIN_to_RGB(self, kelvin ):
        """
        Converts from K to RGB, algorithm courtesy of 
        http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/
        """
        #range check
        if kelvin < 1000: 
            kelvin = 1000
        elif kelvin > 40000:
            kelvin = 40000
    
        tmp_internal = kelvin / 100.0
    
        # red 
        if tmp_internal <= 66:
            red = 255
        else:
            tmp_red = 329.698727446 * math.pow(tmp_internal - 60, -0.1332047592)
            if tmp_red < 0:
                red = 0
            elif tmp_red > 255:
                red = 255
            else:
                red = tmp_red
    
        # green
        if tmp_internal <=66:
            tmp_green = 99.4708025861 * math.log(tmp_internal) - 161.1195681661
            if tmp_green < 0:
                green = 0
            elif tmp_green > 255:
                green = 255
            else:
                green = tmp_green
        else:
            tmp_green = 288.1221695283 * math.pow(tmp_internal - 60, -0.0755148492)
            if tmp_green < 0:
                green = 0
            elif tmp_green > 255:
                green = 255
            else:
                green = tmp_green
    
        # blue
        if tmp_internal >=66:
            blue = 255
        elif tmp_internal <= 19:
            blue = 0
        else:
            tmp_blue = 138.5177312231 * math.log(tmp_internal - 10) - 305.0447927307
            if tmp_blue < 0:
                blue = 0
            elif tmp_blue > 255:
                blue = 255
            else:
                blue = tmp_blue
        
        red = int(red)
        green = int(green)
        blue = int(blue)
            
        return red, green, blue

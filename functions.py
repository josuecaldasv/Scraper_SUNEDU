

## LIBRARIES
# ----------

# Selenium
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains

# Options driver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select

# Dataframes
import pandas as pd
import itertools
import os

# Simulating human behavior
import time
from time import sleep
import random

# Clear data
import unidecode

# Json files
import json
import re
import numpy as np
import itertools
from pandas import json_normalize

# To use explicit waits
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Download files
import urllib.request
import requests
from openpyxl import Workbook

# pytesseract
from PIL import Image
from io import BytesIO
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


## FUNCIONES
# ----------

def init_driver():
    
    '''
    Objetivo:
        - Inicializar el driver
    '''
    
    options = Options()
    service = Service( ChromeDriverManager().install() )
    driver  = webdriver.Chrome( service = service )
    driver.maximize_window()
    return driver


def extract_captcha( segs_r, driver, xpath_image, xpath_captcha ):
    
    '''
    Objetivo:
        - Obtener el código captcha
    '''

    captcha       = WebDriverWait( driver, segs_r ).until( EC.presence_of_element_located( ( By.XPATH, xpath_image ) ) )
    captcha_image = captcha.screenshot_as_png
    captcha_image = Image.open( BytesIO( captcha.screenshot_as_png ) )

    # with open( ruta_img, 'wb' ) as f:
    #     f.write( captcha_image )
        
    clave_valor   = pytesseract.image_to_string( captcha_image,
                                                 config = '-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' ).strip()
    
    return clave_valor


def refresh_popup( segs_r, driver, xpath_popup, xpath_frame, refresh = True ):
    
    '''
    Objetivo:
        - Refrescar el navegador
    '''
    
    if refresh: 
    
        driver.switch_to.default_content()
        driver.refresh()
    
    verificar_titulos_popup = WebDriverWait( driver, segs_r ).until( EC.element_to_be_clickable( ( By.XPATH, xpath_popup ) ) )
    verificar_titulos_popup.click()    
    
    frame_popup = WebDriverWait( driver, segs_r ).until( EC.presence_of_element_located( ( By.XPATH, xpath_frame ) ) )
    driver.switch_to.frame( frame_popup )


def send_keys( segs, driver, xpath_field, key ):
    
    '''
    Objetivo:
        - Rellenar los campos con información
          solicitada: DNI o Captcha
    '''
    
    field = WebDriverWait( driver, segs ).until( EC.element_to_be_clickable( ( By.XPATH, xpath_field ) ) )
    field.clear()
    field.send_keys( key )
    
    
    
def scraper_SUNEDU( df, url, velocidad = 'slow' ):
    
    '''
    Objetivo:
        - Extraer información sobre grados y títulos
          del portal de SUNEDU a partir del DNI
          
    Input:
        - df        : Pandas DataFrame que contiene la columna
                      'dni', la cual indica el DNI de las personas
                      cuyos grados o títulos serán verificados
        - url       : Enlace del portal de SUNEDU
        - velocidad : determina la velocidad con la que opera el 
                      scraper. Tiene tres posibles valores: lento,
                      medio y rápido. Mayor velocidad puede tomar 
                      menos tiempo, pero conducir a más errores y 
                      ciclos de reinicio.
                     
    output: 
        - Pandas DataFrame con columnas adicionales en función
          a la información extraída
    '''
    
    driver = init_driver()
    driver.get( url )
    
    if velocidad == 'slow':
        segs = 30
    elif velocidad == 'medium':
        segs = 10
    else:
        segs = 5
    
    xpath_popup = '//*[@id="dvEnLinea"]/div[2]/div[3]/div/div[2]/div/a'
    xpath_frame = '//*[@id="ifrmShowFormConstancias"]'
    
    refresh_popup( 30, driver, xpath_popup, xpath_frame, refresh = False )
    
    variable_flag = False
    
    df[ 'n_grados' ] = 0
    
    for index, row in df.iterrows():
        
        dni_valor = row[ 'dni' ]
        print( f'Obs.: { index + 1 }' )
        print( f'DNI: { dni_valor }' )
        
        xpath_dni_campo = '//*[@id="doc"]'
        send_keys( segs, driver, xpath_dni_campo, dni_valor )
        
        max_retries = 15

        for retry in range( max_retries ):
        
            try: 

                xpath_image   = '//*[@id="captchaImg"]/img'
                xpath_captcha = '//*[@id="captcha"]'
                clave_valor   = extract_captcha( 20, driver, xpath_image, xpath_captcha )
                
                xpath_captcha_campo = '//*[@id="captcha"]'
                send_keys( segs, driver, xpath_captcha_campo, clave_valor ) 

                buscar_boton = WebDriverWait( driver, 30 ).until( EC.element_to_be_clickable( ( By.XPATH, '//*[@id="buscar"]' ) ) )
                buscar_boton.click()
                
                print( f'Captcha: { clave_valor }' )
                
                try: 
                    
                    sections        = {}
                    result_sections = WebDriverWait( driver, 20 ).until( EC.presence_of_all_elements_located( (By.XPATH, '//*[@id="finalData"]/tr' ) ) )
                    n_grados        = len( result_sections )

                    for i, result in enumerate( result_sections ):
                        
                        boxes = WebDriverWait( driver, segs ).until( EC.presence_of_all_elements_located( ( By.XPATH, f'//*[@id="finalData"]/tr[{ i + 1 }]/td' ) ) )
                        
                        for j, box in enumerate( boxes ):
                            
                            boxes_names_list = { 0: 'datos', 1: 'grado_fecha', 2: 'institucion', 3: 'otro' }
                            box_name = boxes_names_list.get( j )   
                            text     = box.text
                            sections[ f'{ box_name }_{ i }' ] = text

                    row = { 'dni': dni_valor }
                    row.update( sections )
                    df.loc[ index, ['dni', *sections.keys() ] ] = row.values()
                    df.loc[ index, [ 'n_grados' ] ] = n_grados
                    
                    columnas_a_borrar = [ col for col in df.columns if  col.startswith( 'otro' ) ]
                    df                = df.drop( columns = columnas_a_borrar )
                    
                    print( f'Intento N.: { retry }' )
                    print( f'Se saltó el captcha' )
                    print( 'Éxito en extraer datos' )
                    
                    # ruta_img =  f'img/{ clave_valor }.png' 
                    # with open( ruta_img, 'wb' ) as f:
                    #     f.write( captcha_image )

                    refresh_popup( 5, driver, xpath_popup, xpath_frame, refresh = True )  
                    
                    print( 'Pasamos a la siguiente observación' )
                    print( '\n' )

                    break                    
                
                except:   
                
                    error_popup        = WebDriverWait( driver, segs ).until( EC.element_to_be_clickable( ( By.XPATH, '//*[@id="frmError"]' ) ) )
                    class_error_popup  = error_popup.get_attribute( 'class' )
                    caso_no_resultados = 'No se encontraron resultados con este número de DNI'
                    captcha_incorrecto = 'EL código CAPTCHA ingresado'
                    
                    error_msj          = WebDriverWait( driver, segs ).until( EC.presence_of_element_located( ( By.XPATH, '//*[@id="frmError_Body"]/p' ) ) ).text
                    
                    if not error_msj.startswith( caso_no_resultados ):
                        
                        print( f'Intento N.: { retry }' )
                        
                        if error_msj.startswith( captcha_incorrecto ):
                            
                            print( 'Código captcha incorrecto' )
                            
                        else:
                            
                            print( 'El navegador no cargó correctamente' )
                        
                        raise Exception( 'Continuar hacia el bloque except' )
                    
                    else:
                        
                        print( f'Intento N.: { retry }' )
                        print( f'Se saltó el captcha' )
                        print( f'No se encontraron datos para este DNI' )
                        print( 'Pasamos a la siguiente observación' )
                        print( '\n' )   
                        
                        refresh_popup( segs, driver, xpath_popup, xpath_frame, refresh = True ) 
                        
                        variable_flag = True                        
                        
                        break
                    
                if variable_flag:
                    
                    break
                
            except Exception as e:

                print( f'Error en la ejecución' )
                print( f'Intentando de nuevo...' )
                
                try: 
                    
                    boton_x = WebDriverWait( driver, segs ).until( EC.element_to_be_clickable( ( By.XPATH, '//*[@id="closeModalError"]' ) ) )
                    boton_x.click()
                    
                    print( f'Click en botón X' )

                    continue
                    
                except:

                    refresh_popup( segs, driver, xpath_popup, xpath_frame, refresh = True ) 
                    send_keys( segs, driver, xpath_dni_campo, dni_valor )
                    
                    print( f'Se reinicia el navegador' )
                    
                    continue
                    
    driver.quit()
        
    return df
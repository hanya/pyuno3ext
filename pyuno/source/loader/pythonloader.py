#**************************************************************
#  
#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#  
#    http://www.apache.org/licenses/LICENSE-2.0
#  
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.
#  
#**************************************************************
import uno
import unohelper
import sys
import os
from com.sun.star.uno import Exception, RuntimeException
from com.sun.star.loader import XImplementationLoader
from com.sun.star.lang import XServiceInfo

MODULE_PROTOCOL = "vnd.openoffice.pymodule:"
DEBUG = 0

g_supportedServices  = "com.sun.star.loader.Python", 
g_implementationName = "org.openoffice.comp.pyuno.Loader"

def splitUrl(url):
    parts = url.split(":", 1)
    if len(parts) == 1:
        raise RuntimeException("PythonLoader: No protocol in url " + url, None)
    return parts

g_loadedComponents = {}

def checkForPythonPathBesideComponent(url):
    path = unohelper.fileUrlToSystemPath(url + "/pythonpath.zip");
    if DEBUG == 1:
        print("checking for existence of " + encfile(path))
    if os.access(encfile(path), os.F_OK) and not path in sys.path:
        if DEBUG == 1:
            print("adding " + encfile(path) + " to sys.path")
        sys.path.append(path)

    path = unohelper.fileUrlToSystemPath(url + "/pythonpath");
    if os.access(encfile(path), os.F_OK) and not path in sys.path:
        if DEBUG == 1:
            print("adding " + encfile(path) + " to sys.path")
        sys.path.append(path)

def encfile(uni):
    return uni.encode(sys.getfilesystemencoding())

class Loader(XImplementationLoader, XServiceInfo, unohelper.Base):
    def __init__(self, ctx):
        if DEBUG:
            print("pythonloader.Loader ctor")
        self.ctx = ctx

    def getModuleFromUrl(self, url):
        if DEBUG:
            print("pythonloader: interpreting url " + url)
        protocol, dependent = splitUrl(url)
        if "vnd.sun.star.expand" == protocol:
            exp = self.ctx.getValueByName("/singletons/com.sun.star.util.theMacroExpander")
            url = exp.expandMacros(dependent)
            protocol, dependent = splitUrl(url)

        if DEBUG:
            print("pythonloader: after expansion " + protocol + ":" + dependent)

        try:
            if "file" == protocol:
                # remove \..\ sequence, which may be useful e.g. in the build env
                url = unohelper.absolutize(url, url)

                # did we load the module already ?
                mod = g_loadedComponents.get(url)
                if not mod:
                    mod = type(sys)("uno_component")

                    # check for pythonpath.zip beside .py files
                    checkForPythonPathBesideComponent(url[0:url.rfind('/')])

                    # read the file
                    filename = unohelper.fileUrlToSystemPath(url)
                    with open(filename) as f:
                        src = f.read()

                    # compile and execute the module
                    codeobject = compile(src, encfile(filename), "exec")
                    exec(codeobject, mod.__dict__)
                    mod.__file__ = encfile(filename)
                    g_loadedComponents[url] = mod
                return mod
            elif "vnd.openoffice.pymodule" == protocol:
                return  __import__(dependent)
            else:
                raise RuntimeException("PythonLoader: Unknown protocol " +
                                        protocol + " in url " + url, self)
        except ImportError as e:
            raise RuntimeException("Couldn't load " + url + " for reason " + str(e), None)
        return None

    def activate(self, implementationName, dummy, locationUrl, regKey):
        if DEBUG:
            print("pythonloader.Loader.activate")

        mod = self.getModuleFromUrl(locationUrl)
        implHelper = mod.__dict__.get("g_ImplementationHelper" , None)
        if implHelper is None:
            return mod.getComponentFactory(implementationName, self.ctx.getServiceManager(), regKey)
        else:
            return implHelper.getComponentFactory(implementationName, regKey, self.ctx.getServiceManager())

    def writeRegistryInfo(self, regKey, dummy, locationUrl):
        if DEBUG:
            print("pythonloader.Loader.writeRegistryInfo")

        mod = self.getModuleFromUrl(locationUrl)
        implHelper = mod.__dict__.get("g_ImplementationHelper" , None)
        if implHelper is None:
            return mod.writeRegistryInfo(self.ctx.getServiceManager(), regKey)
        else:
            return implHelper.writeRegistryInfo(regKey, self.ctx.getServiceManager())

    def getImplementationName(self):
        return g_implementationName

    def supportsService(self, ServiceName):
        return ServiceName in self.serviceNames

    def getSupportedServiceNames(self):
        return g_supportedServices

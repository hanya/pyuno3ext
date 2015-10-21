
PyUNO Extension for Python 3.X
===========

This provides PyUNO built with Python 3.X for Apache OpenOffice 4.X. 


Supported Environments
---------
* Linux x86_64 (Tested)


Restrictions
---------
* You need write permission to program/services.rdb to disable original Python.
* This extension can not coexist with the default Python.


How to Build
--------
To build extensions, Apache OpenOffice 4.X and its SDK. Setup the SDK 
before starting to build the extension, see sdk/index.html to begin.

    git clone https://github.com/hanya/pyuno3ext
    cd pyuno3ext
    source ~/openoffice4.1_sdk/PC_NAME/setsdkenv_unix.sh
    make

PC_NAME should be name of your computer.

After that you can find the following files in the build directory.
* Python3Loader-VERSION-PLATFORM.oxt
* Python3Script-VERSION.oxt

Install Python3Loader-VERSION-PLATFORM.oxt package first through the Extension Manager. 
And then install Python3Script-VERSION.oxt later. Restart your office. 


How to Use
--------
If you do no have write permission to program/services.rdb file, 
you can not use this extension.
This extension conflict with original Python. So you have to disable 
the original implementations.
Copy tools/pyuno3ext.py file to your USER/Scripts/python directory. 
Execute "Enable_Python3" function through 
Tools - Macros - Macro Organizer - Python window. Then restart your office. 
You can disable Python3 with "Disable_Python3" funciton. 
You can check the current state with "Show_Information" function.


Python Script
--------
You can execute Python macros stored in USER/Scripts/python which 
is the same location with the original Python scripts.


Python Components
--------
The name of the component loader is "com.sun.star.loader.Python3". 
You have to choose the way to register with *.components file to register your components 
written in Python 3. You can see the example in scripting/pythonscript.components and 
scripting/manifest.xml files.
Without components file, you will met error while installing your Python component 
because of the restriction of the extension manager.


Differences between Original PyUNO for Python 2.X
-------

### Classes
* uno.ByteSequence must be initialized with bytes, bytearray or 
ByteSequence instance.


### Replaced import hook ###

PyUNO uses custom import function to import UNO values in uno.py. 
It has some problems when other module uses the same way. 
Import hook is introduced by importlib module on Python 3.1. 
We should be use to import UNO values.
  
hasModule() and getModuleElementNames() methods are introduced 
to get required information about UNO modules in pyuno.
See uno.py more detail.
  
New import hook allows to import module defined in IDL as Python module. 
For example, com.sun.star.beans module can be imported as follows: 
    import com.sun.star.beans
and its sub elements can be accessed as its attribute.
    pv = com.sun.star.beans.PropertyValue()
When enum or constants is requested, it can be imported as modules. 
And its value elements are accessible as module attributes. 
    import com.sun.star.awt.PosSize as PosSize
    print(PosSize.POS)
  
These module attributes are not loaded at import time of the module. 
But once a value is requested, it would be normal attribute of the module. 
No more __getattr__ hook is not called to get the value.


CHANGES
-------
See CHANGES.md file.


LICENSE
--------
Apache License Version 2.0

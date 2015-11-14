
PyUNO Extension for Python 2.7 and 3.X
===========

This provides PyUNO as extension packages built with Python both 2.7 and 3.X 
for Apache OpenOffice 4.X. 
The code is based on Apache OpenOffice revision 1591060.


Supported Environments
---------
* Linux x86_64
* Linux x86


Restrictions
---------
* You need write permission to program/unorc or uno.ini file to disable original Python.
* This extension can not coexist with the default Python.
* ToDo: Python 3.3 might not work well.
* For Python 2.7, import hook based on importlib is not supported.
* No plan to support Python 3.0, 3.1 and 3.2.


How to Build
--------
Please read How to Use section before building the extension.

To build extensions, Apache OpenOffice 4.X and its SDK are required. 
Setup the SDK before starting to build the extension, 
see sdk/index.html to begin with.
Requires libboost-dev to build on Linux environment.

    git clone https://github.com/hanya/pyuno3ext.git
    cd pyuno3ext
    source ~/openoffice4.1_sdk/PC_NAME/setsdkenv_unix.sh
    make

PC_NAME should be name of your computer.

If you want to build for different Python version, you can choose as follows: 

    make PY_MAJOR=3 PY_MINOR=4 PY_BUGFX=3

After that you can find the following files in the build/ directory.
* PythonVERSIONLoader-VERSION-PLATFORM.oxt
* PythonScript-VERSION.oxt

Install PythonVERSIONLoader-VERSION-PLATFORM.oxt package first 
through the Extension Manager. 
And then install Python3Script-VERSION.oxt later. After that restart your office. 

PythonScript package also contains mailmerge.py file which implements 
mailing service used by the mailmerge function.


How to Use
--------
If you do not have write permission to program/unorc or uno.ini file, 
you can not use this extension.
This extension conflict with original Python. So you have to disable 
the original implementations. There are two ways to do.

First way, this might not safe to your extensions. With this ways, 
the order of loading components would change. It might cause some error.
Change UNO_SERVICES variable in program/unorc or uno.ini file as follows.

From 

    UNO_SERVICES=${ORIGIN}/services.rdb ${URE_MORE_SERVICES}

to

    UNO_SERVICES=${URE_MORE_SERVICES} ${ORIGIN}/services.rdb

With this way, components installed by the extensions hidden by 
the services from the office if conflict each other.

The second way is safer than the first one. Copy tools/pyuno3ext.py file 
to your USER/Scripts/python directory. Execute "Create_services_rdb" function 
through Tools - Macros - Macro Organizer - Python window. Store to somewhere 
and edit the UNO_SERVICES variable in program/unorc or uno.ini.

From 

    UNO_SERVICES=${ORIGIN}/services.rdb ${URE_MORE_SERVICES}

to

    UNO_SERVICES=file:///home/user/Documents/services.rdb ${URE_MORE_SERVICES}

path to the rdb file should be match with the location you have saved.

Then restart your office. 
You can check the current state with "Show_Information" function.


Switching between Versions
--------
You can install both Python 2.7 and 3.X extension packages but you can not 
enable both at the same time. You have to use the following procedure to 
switch between them.

1. Choose Tools - Extension Manager in the main menu.
2. Disable enabled one.
3. Enable another one that you want to use.
4. Restart your office.

PythonScript-VERSION.oxt package can be used on the both version. 
You do not need to change its state.


For Interprocess Communication
--------
If you want to use the Python from the extension package, execute 
"Create_Python_sh" function from tools/pyuno3ext.py file. 
It generates helper shell script to execute python executable, 
which has the same function with the original python shipped with the office. 
You can connect to the office instance with it.

Please use "Create_Python2_sh" for Python 2.7 alternatively.


2to3
--------
tools/pyuno3ext.py file contains helper function "Execute_2to3" to execute 
2to3 tool which helps you to migrate your code into Python 3. 
Copy pyuno3ext.py file into USER/Scripts/python directory and execute 
"Execute_2to3" function through Tools - Macros - Macro Organizer - Python.

You can choose a file or content of a directory to analyze on the dialog. 
The result of the analysis will be shown in a Writer document. 
If you want to store the migrated result, choose some options on the dialog. 
You might need additonal modififcations even after the migration on your code.


Python Script
--------
You can execute Python macros stored in USER/Scripts/python which 
is the same location with the original Python scripts.


Python Components
--------
The name of the component loader is the same with the original for 
compatibility reason, use "com.sun.star.loader.Python". 


Changes
-------
All Python 3 related changes influence to your code.

### Classes ###
* uno.ByteSequence must be initialized with bytes, bytearray or 
ByteSequence instance.
* No \__members\__ and \__methods\__ on pyuno instance on Python3. Use dir().


### Replaced import hook ###

PyUNO uses custom import function to import UNO values in uno.py. 
It has some problems when other module uses the same way. 
Import hook is introduced by importlib module on Python 3.1. 
We should use it to import UNO values. 

On Python 2.7 extension, importlib is not used because of limited support 
of the module. It still uses import hack but it supports module import 
and other new importable values.

hasModule(), getModuleElementNames() and importValue() methods have been
introduced to get required information about UNO modules in pyuno.

There is no changes on existing import such as: 

    from com.sun.star.beans import PropertyValue

You could import the following things of UNO in the former PyUNO: 

* interface
* struct
* exception
* enum value
* constant value
* type

Additionally, you can import the following values:

* module
* service
* singleton
* enum
* constants group

New import hook allows you to import module defined in IDL as Python module. 
For example, com.sun.star.beans module can be imported as follows:

    import com.sun.star.beans

and its sub elements can be accessed as its attribute.

    pv = com.sun.star.beans.PropertyValue()

When enum or constants group is requested, it can be imported as modules. 
And its value elements are accessible as module attributes. 

    import com.sun.star.awt.PosSize as PosSize
    print(PosSize.POS)

These module attributes are not loaded at import time of the module. 
But once a value is requested, it would be normal attribute of the module. 
The \__getattr\__ hook is not called to get the value anymore.

Constructors are defined on the some services which provides the way to 
instantiate service without using com.sun.star.lang.XMultiComponentFactory. 
And also it provides way to check parameters before to pass them to the 
service to instantiate.

    from com.sun.star.rdf import URI
    uri = URI.create("foo")

A service has no defined constructor has "create" method as its constructor. 
No parameter check is provided in this case.

    from com.sun.star.frame import Desktop
    desktop = Desktop.create()

It can take any number of parameters the create method if you need some 
initialization parameters. This method is different from the constructor 
defined in the their IDL.

Within this way to call constructors, you can not specify the current context. 
Use com::sun::star::lang::XMultiServiceFactory interface instead if you 
need specific context.

You can import only registerd services in the office registry. If you want 
to instantiate your own service installed by your extension, the extension 
have to contain the registry for own services.

In the case of singletons, you can import it and get its instance as follows: 

    from com.sun.star.deployment import PackageInformationProvider
    pip = PackageInformationProvider.get()


CHANGES
-------
See CHANGES.md file.


LICENSE
--------
Apache License Version 2.0

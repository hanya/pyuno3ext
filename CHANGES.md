
Original files are came from Apache OpenOffice repository revision 1591060. 
Changes are summarized below: 

* pythonloader: make it can find the configuration file based on the library location
* mailmerge: to match with Python3 import
* mailmerge: pass bytearray from bytesequence of attachments
* mailmerge: use SMTP_SSL when SSL type is choosen
* pyuno: replace import hack with import hook
* pyuno: supports UNO module import
* pyuno: singleton getter support
* pyuno: service constructor support
* pyuno: order of checking attribute name changed in PyUNO_getter
* pyuno: UNO value import based on part of import hook
* pythonscript: without imp module to instantiate new module
* python.sh: embedded in tools/pyuno3ext.py file and change environmental variables

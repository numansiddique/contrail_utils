Log customization in OpenContrail
--------------------------------

OpenContrail supports log configuration in three ways
 1. Use the default logging provided by OpenContrail.
 2. Define your own log configuration file using based on the python logging
    https://docs.python.org/2/library/logging.config.html#module-logging.config
 3. Define new logging mechanism by implementing a new logger.
 
 
 The file 'contrail_oslo_logger.py' defines a logging mechanism by using the
 oslo logging.
 
 Using this approach, the user can use the same logging format used in other OpenStack components.
 
 To use 'contrail_oslo_logger.py' in your setup define the below parameters in
 the default section of your contrail configuration files
 
 logger_class = contrail_oslo_logger.ContrailOsloLogger
 
 logging_conf = /etc/contrail/contrail-oslo-sample.conf
 
 
Make sure that 'contrail_oslo_logger.py' is loadable.
Copying this file to '/usr/lib/python2.7/dist-packages/pysandesh/'
would work.




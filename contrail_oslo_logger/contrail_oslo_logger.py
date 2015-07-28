#    Copyright 2015 Redhat Inc
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os

from oslo_config import cfg
from oslo_log import log as logging

from pysandesh import sandesh_base_logger


class ContrailOsloLogger(sandesh_base_logger.SandeshBaseLogger):
    def __init__(self, generator, logger_config_file=None):
        if not os.path.exists(logger_config_file):
            raise Exception('%s file not present ' % logger_config_file)

        opts = [
            cfg.StrOpt('test', default=None),
        ]
        args = ['--config-file', logger_config_file]
        logging.set_defaults()
        logging.register_options(cfg.CONF)
        cfg.CONF(args=args)
        # there is a bug in older versions of oslo_config. This is
        # just a workaround
        cfg.CONF.register_opts(opts)
        logging.setup(cfg.CONF, "contrail")
        self._logger = logging.getLogger(generator)

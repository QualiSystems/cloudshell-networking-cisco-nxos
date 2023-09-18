from __future__ import annotations

import time
from collections import OrderedDict

from cloudshell.networking.cisco.command_actions.system_actions import SystemActions
from cloudshell.networking.cisco.flows.cisco_configuration_flow import (
    CiscoConfigurationFlow,
)
from cloudshell.shell.flows.configuration.basic_flow import (
    ConfigurationType,
    RestoreMethod,
)
from cloudshell.shell.flows.utils.url import BasicLocalUrl, RemoteURL


class CiscoNXOSConfigurationFlow(CiscoConfigurationFlow):
    STARTUP_LOCATION = BasicLocalUrl.from_str("startup-config", "/")
    RUNNING_LOCATION = BasicLocalUrl.from_str("running-config", "/")
    BACKUP_STARTUP_LOCATION = BasicLocalUrl.from_str("backup-sc", "bootflash:")
    TEMP_CONFIG_LOCATION = BasicLocalUrl.from_str("local-copy", "bootflash:")

    def _restore_flow(
        self,
        config_path: RemoteURL | BasicLocalUrl,
        configuration_type: ConfigurationType,
        restore_method: RestoreMethod,
        vrf_management_name: str | None,
    ) -> None:
        """Execute flow which save selected file to the provided destination.

        :param path: the path to the configuration file, including the
                     configuration file name
        :param restore_method: the restore method to use when restoring the
                               configuration file. Possible Values are append
                               and override
        :param configuration_type: the configuration type to restore. Possible
                                   values are startup and running
        :param vrf_management_name: Virtual Routing and Forwarding Name
        """
        config_type = configuration_type.value
        if "-config" not in config_type:
            config_type += "-config"
        with self._cli_handler.get_cli_service(
            self._cli_handler.enable_mode
        ) as enable_session:
            restore_action = SystemActions(enable_session, self._logger)
            reload_action_map = self._prepare_reload_act_map()

            if restore_method.value == "override":
                is_backup_created = False
                if self._cli_handler.cli_type.lower() != "console":
                    raise Exception(
                        self.__class__.__name__,
                        "Unsupported cli session type: {}. "
                        "Only Console allowed for restore override".format(
                            self._cli_handler.cli_type.lower()
                        ),
                    )

                restore_action.copy(
                    source=config_path.safe_url,
                    destination=self.TEMP_CONFIG_LOCATION.filename,
                    vrf=vrf_management_name,
                    action_map=restore_action.prepare_action_map(
                        config_path, self.TEMP_CONFIG_LOCATION
                    ),
                )
                try:
                    restore_action.copy(
                        source=self.STARTUP_LOCATION.filename,
                        destination=self.BACKUP_STARTUP_LOCATION.filename,
                        action_map=restore_action.prepare_action_map(
                            self.STARTUP_LOCATION, self.BACKUP_STARTUP_LOCATION
                        ),
                    )
                    is_backup_created = True
                except Exception as e:
                    self._logger.warning(
                        "Failed to backup startup-config. " "Error: {}".format(str(e))
                    )

                restore_action.write_erase()
                restore_action.reload_device_via_console(action_map=reload_action_map)

                restore_action.copy(
                    source=self.TEMP_CONFIG_LOCATION.filename,
                    destination=self.RUNNING_LOCATION.filename,
                    action_map=restore_action.prepare_action_map(
                        self.TEMP_CONFIG_LOCATION, self.RUNNING_LOCATION
                    ),
                )

                time.sleep(5)
                if is_backup_created:
                    restore_action.copy(
                        source=self.BACKUP_STARTUP_LOCATION.filename,
                        destination=self.STARTUP_LOCATION.filename,
                        action_map=restore_action.prepare_action_map(
                            self.BACKUP_STARTUP_LOCATION, self.STARTUP_LOCATION
                        ),
                        timeout=200,
                    )

            elif (
                "startup" in configuration_type.value
                and restore_method == RestoreMethod.APPEND
            ):
                raise Exception(
                    self.__class__.__name__,
                    "Restore of startup config in append mode is not supported",
                )
            else:
                target_config_path = BasicLocalUrl.from_str(config_type, "/")
                restore_action.copy(
                    source=config_path.safe_url,
                    destination=target_config_path.filename,
                    vrf=vrf_management_name,
                    action_map=restore_action.prepare_action_map(
                        config_path, target_config_path
                    ),
                )

    def _prepare_reload_act_map(self):
        action_map = OrderedDict()
        # Proceed with reload? [confirm]
        action_map[
            (
                r"[Aa]bort\s+[Pp]ower\s+[Oo]n\s+[Aa]uto\s+"
                r"[Pp]rovisioning.*[\(\[].*[Nn]o[\]\)]"
            )
        ] = lambda session, logger: session.send_line("yes", logger)
        action_map[
            r"[Ee]nter\s+system\s+maintenance\s+mode.*[\[\(][Yy](es)?\/[Nn](o)?[\)\]] "
        ] = lambda session, logger: session.send_line("n", logger)
        action_map[
            r"[Ss]tandby card not present or not [Rr]eady for failover]"
        ] = lambda session, logger: session.send_line("y", logger)
        action_map[
            r"[Pp]roceed with reload"
        ] = lambda session, logger: session.send_line(" ", logger)
        action_map[r"reboot.*system"] = lambda session, logger: session.send_line(
            "y", logger
        )
        action_map[
            r"[Ww]ould you like to enter the basic configuration dialog"
        ] = lambda session, logger: session.send_line("n", logger)
        action_map[
            r"[Dd]o you want to enforce secure password standard"
        ] = lambda session, logger: session.send_line("n", logger)
        # Since as a part of restore override we are doing complete configuration erase,
        # switching Login action map to use default NXOS username - admin
        action_map[
            "[Ll]ogin:|[Uu]ser:|[Uu]sername:"
        ] = lambda session, logger: session.send_line("admin", logger)
        action_map["[Pp]assword.*(:)?"] = lambda session, logger: session.send_line(
            self._cli_handler.password, logger
        )
        action_map[r"\[confirm\]"] = lambda session, logger: session.send_line(
            "y", logger
        )
        action_map[r"continue"] = lambda session, logger: session.send_line("y", logger)
        action_map[r"\(y\/n\)"] = lambda session, logger: session.send_line("n", logger)
        action_map[
            r"[\[\(][Yy]es/[Nn]o[\)\]]"
        ] = lambda session, logger: session.send_line("n", logger)
        action_map[r"[\[\(][Nn]o[\)\]]"] = lambda session, logger: session.send_line(
            "n", logger
        )
        action_map[r"[\[\(][Yy]es[\)\]]"] = lambda session, logger: session.send_line(
            "n", logger
        )
        action_map[
            r"[\[\(][Yy]/[Nn][\)\]]"
        ] = lambda session, logger: session.send_line("n", logger)

        return action_map

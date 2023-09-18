#!/usr/bin/python
from typing import ClassVar

from cloudshell.cli.factory.session_factory import (
    ConsoleSessionFactory,
    GenericSessionFactory,
    SessionFactory,
)
from cloudshell.cli.service.cli_service_impl import CliServiceImpl
from cloudshell.cli.session.console_ssh import ConsoleSSHSession
from cloudshell.cli.session.ssh_session import SSHSession
from cloudshell.cli.session.telnet_session import TelnetSession
from cloudshell.networking.cisco.cli.cisco_cli_handler import CiscoCli, CiscoCliHandler
from cloudshell.networking.cisco.cli.cisco_command_modes import (
    ConfigCommandMode,
    EnableCommandMode,
)

from cloudshell.networking.cisco.nxos.cli.cisco_nxos_console_sessions import (
    NXOSConsoleTelnetSession,
)


class CiscoNXOSCli(CiscoCli):
    def get_cli_handler(self, resource_config, logger):
        return CiscoNXOSCliHandler.from_config(resource_config, logger, self.cli)


class CiscoNXOSCliHandler(CiscoCliHandler):
    REGISTERED_SESSIONS: ClassVar[tuple[SessionFactory]] = (
        GenericSessionFactory(SSHSession),
        GenericSessionFactory(TelnetSession),
        ConsoleSessionFactory(ConsoleSSHSession),
        ConsoleSessionFactory(
            NXOSConsoleTelnetSession, session_kwargs={"start_with_new_line": False}
        ),
        ConsoleSessionFactory(
            NXOSConsoleTelnetSession, session_kwargs={"start_with_new_line": True}
        ),
    )

    @property
    def cli_type(self):
        return self._cli_type

    @property
    def password(self):
        return self._auth.password

    def _on_session_start(self, session, logger):
        """Send default commands to configure/clear session outputs.

        :return:
        """
        cli_service = CliServiceImpl(
            session=session, requested_command_mode=self.enable_mode, logger=logger
        )
        cli_service.send_command("terminal length 0", EnableCommandMode.PROMPT)
        cli_service.send_command("terminal width 300", EnableCommandMode.PROMPT)
        with cli_service.enter_mode(self.config_mode) as config_session:
            config_session.send_command("no logging console", ConfigCommandMode.PROMPT)

from cloudshell.cli.session.console_telnet import ConsoleTelnetSession
from cloudshell.cli.types import T_ACTION_MAP


class NXOSConsoleTelnetSession(ConsoleTelnetSession):
    @property
    def _connect_action_map(self) -> T_ACTION_MAP:
        action_map = {
            "[Ll]ogin:|[Uu]ser:|[Uu]sername:": lambda s, l: s.send_line(s.username, l),
            "[Pp]assword(:)?": lambda s, l: s.send_line(s.password, l),
        }
        return action_map

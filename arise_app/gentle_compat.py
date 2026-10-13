"""Use the installed Shell's declared Pi floor instead of a single release check."""
import re


def pi_floor(package):
    peer=package.get('peerDependencies',{}).get('@earendil-works/pi-coding-agent','')
    match=re.fullmatch(r'>=(\d+)\.(\d+)\.(\d+)',peer)
    if match:return tuple(map(int,match.groups()))
    if package.get('version')=='4.0.0':return (0,99,1)
    if package.get('version')=='4.2.0':return (1,2,0)
    return None


def require_compatible_pi(package, version):
    floor=pi_floor(package)
    if not floor:return
    match=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)',version or '')
    if not match or tuple(map(int,match.groups()))<floor:
        raise RuntimeError(f"Gentle {package.get('version','')} necesita Pi {'.'.join(map(str,floor))} o superior. Configura Gentle para actualizar su propio motor.")

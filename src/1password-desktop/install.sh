#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
fail() { echo "1password-desktop: $*" >&2; exit 1; }
[[ $(id -u) == 0 ]] || fail 'Installation requires root.'
[[ ${HOSTCLIGID:-} =~ ^[0-9]{1,10}$ ]] || fail 'hostCliGid is required and must be a decimal GID.'
gid=$((10#$HOSTCLIGID))
(( gid > 0 && gid < 4294967295 )) || fail 'hostCliGid must be between 1 and 4294967294.'
[[ ${ACCEPTRUNTIMEOVERRIDE:-false} == true ]] || fail 'Set acceptRuntimeOverride=true only after accepting the documented global XDG_RUNTIME_DIR override.'
[[ -f /etc/debian_version ]] || fail 'Only Debian/Ubuntu apt images are supported.'
remote=${_REMOTE_USER:-root}
getent passwd "$remote" >/dev/null || fail 'Remote user must exist before installation.'
if getent group "$gid" >/dev/null; then
    group=$(getent group "$gid" | cut -d: -f1)
    [[ $group == onepassword-cli ]] || fail "GID $gid is already allocated to another group; choose an image without this collision. No groups were modified."
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg python3 sudo
curl -fsS https://downloads.1password.com/linux/keys/1password.asc -o /tmp/1password-desktop-key.asc
gpg --batch --yes --dearmor -o /usr/share/keyrings/1password-archive-keyring.gpg /tmp/1password-desktop-key.asc
printf 'deb [arch=%s signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/%s stable main\n' "$(dpkg --print-architecture)" "$(dpkg --print-architecture)" > /etc/apt/sources.list.d/1password.list
install -d /etc/debsig/policies/AC2D62742012EA22 /usr/share/debsig/keyrings/AC2D62742012EA22
curl -fsS https://downloads.1password.com/linux/debian/debsig/1password.pol -o /etc/debsig/policies/AC2D62742012EA22/1password.pol
gpg --batch --yes --dearmor -o /usr/share/debsig/keyrings/AC2D62742012EA22/debsig.gpg /tmp/1password-desktop-key.asc
rm /tmp/1password-desktop-key.asc
apt-get update
apt-get install -y --no-install-recommends 1password-cli
chown "0:$gid" /usr/bin/op
chmod 2755 /usr/bin/op
install -d -m 0755 /usr/local/share/1password-desktop /run/1password-desktop
install -m 0755 configure-user.py /usr/local/share/1password-desktop/configure-user.py
install -m 0755 doctor.py /usr/local/bin/1password-desktop-doctor
python3 - "$remote" "$gid" <<'PY'
import json, sys
with open('/usr/local/share/1password-desktop/config.json', 'w') as f:
    json.dump({'user': sys.argv[1], 'gid': int(sys.argv[2])}, f)
PY
# The helper accepts no arguments, reads only root-owned configuration, and
# drops privileges before touching the remote user's configuration.
printf 'ALL ALL=(root) NOPASSWD: /usr/local/share/1password-desktop/configure-user.py ""\n' > /etc/sudoers.d/1password-desktop
chmod 0440 /etc/sudoers.d/1password-desktop
visudo -cf /etc/sudoers.d/1password-desktop

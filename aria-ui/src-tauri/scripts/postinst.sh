#!/bin/sh
# postinst script for zana
set -e

case "$1" in
    configure)
        echo ""
        echo "  \033[1;35m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
        echo "    \033[1mZANA CORE ESTÁ LISTO PARA SERVIR.\033[0m"
        echo "    \033[1;32mJUNTOS HACEMOS TEMBLAR LOS CIELOS.\033[0m"
        echo "  \033[1;35m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
        echo ""
        echo "  Iniciando Córtex visual..."
        
        if [ -n "$SUDO_USER" ]; then
            # Attempt to launch the app as the user who ran sudo
            # We use a subshell and disown to avoid blocking apt
            (sudo -u "$SUDO_USER" DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u "$SUDO_USER")/bus zana-desktop > /dev/null 2>&1 &) || true
            echo "  ✓ ZANA ha sido invocado. Revisa tu barra de tareas."
        else
            echo "  Busca 'ZANA' en tu lanzador de aplicaciones"
            echo "  o inicia el córtex con: \033[1mzana-desktop\033[0m"
        fi
        echo ""
    ;;
esac

exit 0

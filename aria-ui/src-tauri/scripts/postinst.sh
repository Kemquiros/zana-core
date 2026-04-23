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
        echo "  Instalación completa."
        echo "  Busca 'ZANA' en tu lanzador de aplicaciones"
        echo "  o inicia el córtex manualmente con: \033[1mzana-desktop\033[0m"
        echo ""
    ;;
esac

exit 0

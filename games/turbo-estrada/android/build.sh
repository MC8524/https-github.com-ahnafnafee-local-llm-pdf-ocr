#!/usr/bin/env bash
# Gera o APK do Turbo Estrada sem Gradle/Android Studio.
# Requisitos (Ubuntu/Debian): sudo apt install aapt dalvik-exchange apksigner zipalign android-sdk-platform-23
# Uso: ./build.sh            -> build/turbo-estrada.apk
# Assinatura: usa $KEYSTORE (+ $KEYSTORE_PASS) se definido; senão cria build/debug.keystore.
set -euo pipefail
cd "$(dirname "$0")"

ANDROID_JAR=${ANDROID_JAR:-/usr/lib/android-sdk/platforms/android-23/android.jar}
OUT=build
rm -rf "$OUT/gen" "$OUT/classes" "$OUT/assets" "$OUT"/*.apk "$OUT"/*.dex
mkdir -p "$OUT/gen" "$OUT/classes" "$OUT/assets"

cp ../index.html "$OUT/assets/index.html"

aapt package -f -M AndroidManifest.xml -S res -A "$OUT/assets" -I "$ANDROID_JAR" \
  -J "$OUT/gen" -F "$OUT/unsigned.apk"

javac --release 8 -nowarn -classpath "$ANDROID_JAR" -d "$OUT/classes" \
  $(find src "$OUT/gen" -name '*.java') 2>&1 | grep -v '^Picked up' || true

dalvik-exchange --dex --output="$OUT/classes.dex" "$OUT/classes"
(cd "$OUT" && aapt add unsigned.apk classes.dex >/dev/null)

zipalign -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"

KEYSTORE=${KEYSTORE:-$OUT/debug.keystore}
KEYSTORE_PASS=${KEYSTORE_PASS:-android}
if [ ! -f "$KEYSTORE" ]; then
  keytool -genkeypair -keystore "$KEYSTORE" -storepass "$KEYSTORE_PASS" -keypass "$KEYSTORE_PASS" \
    -alias turbo -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=Turbo Estrada, O=Turbo Estrada, C=BR" 2>&1 | grep -v '^Picked up' || true
fi
apksigner sign --ks "$KEYSTORE" --ks-pass "pass:$KEYSTORE_PASS" \
  --out "$OUT/turbo-estrada.apk" "$OUT/aligned.apk"
apksigner verify "$OUT/turbo-estrada.apk"
rm -f "$OUT/unsigned.apk" "$OUT/aligned.apk" "$OUT"/*.idsig
echo "OK: $OUT/turbo-estrada.apk"

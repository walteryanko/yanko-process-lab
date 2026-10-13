const { withAppBuildGradle, withGradleProperties } = require("@expo/config-plugins");
module.exports = (config) =>
  withAppBuildGradle(withGradleProperties(config, (c) => {
    const key = "reactNativeArchitectures", value = "arm64-v8a,x86_64";
    const item = c.modResults.find(p => p.type === "property" && p.key === key);
    if (item) item.value = value;
    else c.modResults.push({type: "property", key, value});
    return c;
  }), (c) => {
    let s = c.modResults.contents;
    if (!s.includes("PROCESSLAB_SIGNING")) {
      s = s.replace(
        "signingConfigs {",
        `signingConfigs {
        processlab {
            // PROCESSLAB_SIGNING: credentials supplied at build time, never committed.
            storeFile file(System.getenv('PROCESSLAB_KEYSTORE') ?: 'evaluation.keystore')
            storePassword System.getenv('PROCESSLAB_STORE_PASSWORD') ?: 'evaluation-only'
            keyAlias System.getenv('PROCESSLAB_KEY_ALIAS') ?: 'processlab-evaluation'
            keyPassword System.getenv('PROCESSLAB_KEY_PASSWORD') ?: 'evaluation-only'
        }`,
      );
      s = s.replace(
        /release \{\s*\/\/[^]*?signingConfig signingConfigs.debug/,
        (match) =>
          match.replace("signingConfigs.debug", "signingConfigs.processlab"),
      );
      // Match templates that omit the signing comment.
      s = s.replace(
        /release \{\s*signingConfig signingConfigs.debug/,
        "release {\n            signingConfig signingConfigs.processlab",
      );
    }
    // ABI splits disable React Native's defaultConfig NDK filtering and let a
    // universal split collect partial 32-bit AARs. Use one filtered APK instead.
    s = s.replace(/\s*splits\s*\{\s*abi\s*\{[^}]*include 'arm64-v8a', 'x86_64'[^}]*\}\s*\}/g, "\n");
    if (!s.includes("PROCESSLAB_NDK_ABIS")) {
      if (!s.includes("defaultConfig {")) throw new Error("Android template lacks defaultConfig");
      s = s.replace("defaultConfig {", `defaultConfig {
        // PROCESSLAB_NDK_ABIS: complete 64-bit runtime and matching third-party JNI libraries.
        ndk { abiFilters 'arm64-v8a', 'x86_64' }`);
    }
    c.modResults.contents = s;
    return c;
  });

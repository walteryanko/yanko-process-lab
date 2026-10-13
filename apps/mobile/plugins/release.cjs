const { withAppBuildGradle } = require("@expo/config-plugins");
module.exports = (config) =>
  withAppBuildGradle(config, (c) => {
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
      s = s.replace(
        "buildTypes {",
        `splits {
        abi {
            reset()
            enable true
            universalApk true
            include 'arm64-v8a', 'x86_64'
        }
    }
    buildTypes {`,
      );
    }
    s = s.replace(/universalApk false/g, "universalApk true");
    if (!s.includes("PROCESSLAB_SUPPORTED_ABIS")) {
      if (!s.includes("jniLibs {")) throw new Error("Android template lacks JNI packaging configuration");
      s = s.replace("jniLibs {", `jniLibs {
            // PROCESSLAB_SUPPORTED_ABIS: AAR dependencies also contain incomplete 32-bit variants.
            excludes += ['lib/armeabi-v7a/**', 'lib/x86/**']`);
    }
    c.modResults.contents = s;
    return c;
  });

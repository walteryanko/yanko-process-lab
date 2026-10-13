const {withAppBuildGradle}=require('@expo/config-plugins');
module.exports=config=>withAppBuildGradle(config,c=>{
 let s=c.modResults.contents;
 if(!s.includes('PROCESSLAB_SIGNING')){
  s=s.replace('signingConfigs {',`signingConfigs {
        processlab {
            // PROCESSLAB_SIGNING: credentials supplied at build time, never committed.
            storeFile file(System.getenv('PROCESSLAB_KEYSTORE') ?: 'evaluation.keystore')
            storePassword System.getenv('PROCESSLAB_STORE_PASSWORD') ?: 'evaluation-only'
            keyAlias System.getenv('PROCESSLAB_KEY_ALIAS') ?: 'processlab-evaluation'
            keyPassword System.getenv('PROCESSLAB_KEY_PASSWORD') ?: 'evaluation-only'
        }`);
  s=s.replace(/release \{\s*\/\/[^]*?signingConfig signingConfigs.debug/,match=>match.replace('signingConfigs.debug','signingConfigs.processlab'));
  // Match templates that omit the signing comment.
  s=s.replace(/release \{\s*signingConfig signingConfigs.debug/,'release {\n            signingConfig signingConfigs.processlab');
  s=s.replace('buildTypes {',`splits {
        abi {
            reset()
            enable true
            universalApk false
            include 'arm64-v8a', 'x86_64'
        }
    }
    buildTypes {`);
 }
 c.modResults.contents=s;return c;
});

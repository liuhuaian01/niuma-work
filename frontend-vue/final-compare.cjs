const f=require("fs");

// Compare prototype workspace vs components-base workspace
const proto=f.readFileSync("E:/05-超级牛马/super-niuma/frontend/niuma-neon-pulse-prototype.html","utf8");
const base=f.readFileSync("E:/05-超级牛马/super-niuma/frontend-vue/public/css/components-base.css","utf8");

console.log("=== PROTOTYPE .workspace CSS ===");
var idx=proto.indexOf(".workspace {");
if(idx>=0) {
  var end=proto.indexOf("}",idx);
  console.log(proto.substring(idx,end+1));
} else {
  console.log("NOT FOUND");
}

console.log("\n=== EXTRACTED .workspace CSS ===");
idx=base.indexOf(".workspace {");
if(idx>=0) {
  var end=base.indexOf("}",idx);
  console.log(base.substring(idx,end+1));
}

console.log("\n=== PROTOTYPE .content-area CSS ===");
idx=proto.indexOf(".content-area {");
if(idx>=0) {
  var end=proto.indexOf("}",idx);
  console.log(proto.substring(idx,end+1));
}

console.log("\n=== EXTRACTED .content-area CSS ===");
idx=base.indexOf(".content-area {");
if(idx>=0) {
  var end=base.indexOf("}",idx);
  console.log(base.substring(idx,end+1));
}

// Compare nav-rail
console.log("\n=== PROTOTYPE .nav-rail CSS ===");
idx=proto.indexOf(".nav-rail {");
if(idx>=0) {
  var end=proto.indexOf("}",idx);
  console.log(proto.substring(idx,end+1));
}

console.log("\n=== EXTRACTED .nav-rail CSS ===");
idx=base.indexOf(".nav-rail {");
if(idx>=0) {
  var end=base.indexOf("}",idx);
  console.log(base.substring(idx,end+1));
}

// Compare main-content
console.log("\n=== PROTOTYPE .main-content CSS ===");
idx=proto.indexOf(".main-content {");
if(idx>=0) {
  var end=proto.indexOf("}",idx);
  console.log(proto.substring(idx,end+1));
}

console.log("\n=== EXTRACTED .main-content CSS ===");
idx=base.indexOf(".main-content {");
if(idx>=0) {
  var end=base.indexOf("}",idx);
  console.log(base.substring(idx,end+1));
}

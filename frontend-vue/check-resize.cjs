const f=require("fs");
const cc=f.readFileSync("E:/05-超级牛马/super-niuma/frontend-vue/public/css/chat-components.css","utf8");
var idx=cc.indexOf(".resize-handle.active");
if(idx>=0) {
  var end=cc.indexOf("}",idx);
  console.log(cc.substring(idx,end+1));
} else {
  console.log("No .resize-handle.active in chat-components");
}
idx=cc.indexOf(".resize-handle.active");
if(idx<0) {
  // Check components-base
  var base=f.readFileSync("E:/05-超级牛马/super-niuma/frontend-vue/public/css/components-base.css","utf8");
  idx=base.indexOf(".resize-handle.active");
  if(idx>=0) {
    var end=base.indexOf("}",idx);
    console.log("base.css: " + base.substring(idx,end+1));
  } else {
    console.log("No .resize-handle.active in base either");
  }
}

// Check prototype
var proto=f.readFileSync("E:/05-超级牛马/super-niuma/frontend/niuma-neon-pulse-prototype.html","utf8");
idx=proto.indexOf("resize-handle.active");
if(idx>=0) {
  console.log("\nPrototype has resize-handle.active");
} else {
  idx=proto.indexOf("resize-handle");
  if(idx>=0) {
    var end=proto.indexOf(">",idx)+1;
    console.log("\nPrototype resize-handle element:");
    console.log(proto.substring(idx,Math.min(end+100,proto.length)));
  }
}

const f=require("fs");
const cc=f.readFileSync("E:/05-超级牛马/super-niuma/frontend-vue/public/css/chat-components.css","utf8");

// Find ALL side-panel CSS rules
var idx=0;
var count=0;
while((idx=cc.indexOf(".side-panel",idx))>=0 && count<20) {
  var lineStart=cc.lastIndexOf("\n",idx);
  var end=cc.indexOf("}",idx);
  var rule=cc.substring(lineStart+1,end+1).trim();
  if(rule.startsWith(".side-panel")||rule.startsWith(".workspace")) {
    console.log("Rule " + count + ":");
    console.log(rule);
    console.log("");
    count++;
  }
  idx=end;
}

// Also check for page-chat rules that affect side-panel
console.log("=== .workspace.page-chat .side-panel ===");
idx=cc.indexOf(".workspace.page-chat .side-panel");
if(idx>=0) {
  var end=cc.indexOf("}",idx);
  console.log(cc.substring(idx,end+1));
}

// Check the CSS for side-panel open state
console.log("\n=== .side-panel.open ===");
idx=cc.indexOf(".side-panel.open");
if(idx>=0) {
  var end=cc.indexOf("}",idx);
  console.log(cc.substring(idx,end+1));
}

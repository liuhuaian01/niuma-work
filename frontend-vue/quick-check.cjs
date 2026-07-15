const f=require("fs");
const cc=f.readFileSync("E:/05-超级牛马/super-niuma/frontend-vue/public/css/chat-components.css","utf8");

function findRule(css,selector) {
  var idx=css.indexOf(selector);
  if(idx>=0) {
    var end=css.indexOf("}",idx);
    return css.substring(idx,end+1);
  }
  return "NOT FOUND";
}

console.log("=== .chat-area ===");
console.log(findRule(cc,".chat-area {"));

console.log("\n=== .resize-handle ===");
console.log(findRule(cc,".resize-handle {"));

/**
 * Every element in this app is built with `el()`. There is no innerHTML
 * anywhere in this codebase -- text passed here becomes a DOM text node
 * (via createTextNode), which the browser never parses as HTML. That's
 * what "no raw innerHTML for template strings" means in practice: not
 * remembering to escape user input, but never having a code path where
 * user input *could* be interpreted as markup in the first place.
 */
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);

  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") {
      node.className = value;
    } else if (key === "value") {
      node.value = value;
    } else if (key === "checked" || key === "disabled") {
      node[key] = !!value;
    } else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else {
      node.setAttribute(key, value);
    }
  }

  for (const child of [].concat(children)) {
    if (child === null || child === undefined || child === false) continue;
    node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }

  return node;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function mount(parent, node) {
  clear(parent);
  parent.appendChild(node);
}

// Vanilla JS to change the loading message
window.setTimeout(function () {
  document.getElementById("waiter").innerHTML = "This may take some time…";
}, 4000);
window.setTimeout(function () {
  document.getElementById("waiter").innerHTML =
    "It's longer than expected!<br>You're runing the dev version.<br>Please make sure ViteJS server is running.";
}, 10000);

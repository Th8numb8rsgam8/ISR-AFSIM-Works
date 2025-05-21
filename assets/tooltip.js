window.dccFunctions = window.dccFunctions || {};

window.dccFunctions.convertToHMS = function(value) {
   const date = new Date(value * 1000);
   return `${date.toISOString()}`
}
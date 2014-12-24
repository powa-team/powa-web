$(document).foundation();

$(function () {
  var startDate = moment().subtract('days', 1).subtract('months', 1),
      endDate = moment().subtract('days', 1),
      format = 'MMMM D, YYYY';

  $('#date-range').daterangepicker({
    startDate: startDate,
    endDate: endDate,
    minDate: '01/01/2012',
    maxDate: '12/31/2014',
    dateLimit: { days: 60 },
    showDropdowns: true,
    showWeekNumbers: false,
    timePicker: false,
    timePickerIncrement: 1,
    timePicker12Hour: true,
    ranges: {
      'Today': [moment(), moment()],
      'Yesterday': [moment().subtract('days', 1), moment().subtract('days', 1)],
      'Last 7 Days': [moment().subtract('days', 6), moment()],
      'Last 30 Days': [moment().subtract('days', 29), moment()],
      'This Month': [moment().startOf('month'), moment()],
      'Last Month': [moment().subtract('month', 1).startOf('month'), moment().subtract('month', 1).endOf('month')],
      'This Year': [moment().startOf('year'), moment()]
    },
    opens: 'left',
    format: 'MM/DD/YYYY',
    separator: ' to ',
    locale: {
      applyLabel: 'Apply',
      fromLabel: 'From',
      toLabel: 'To',
      customRangeLabel: 'Custom Range',
      daysOfWeek: ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr','Sa'],
      monthNames: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
      firstDay: 1
    }
  }, function(start, end) {
    console.log("Callback has been called!");
    this.element.find('span').html(start.format(format) + ' - ' + end.format(format));
  });
  //Set the initial state of the picker label
  $('#date-range span').html(startDate.format(format) + ' - ' + endDate.format(format));
});

define(['moment'], function(moment){
    var STRINGS = {
        nodiff: '0',
        year: 'year',
        years: 'years',
        month: 'month',
        months: 'months',
        day: 'day',
        days: 'days',
        hour: 'hour',
        hours: 'hours',
        minute: 'min',
        minutes: 'min',
        second: 's',
        seconds: 's',
        millisecond: 'ms',
        milliseconds: 'ms',
        delimiter: ' '
    };
    moment.fn.preciseDiff = function(d2) {
        return moment.preciseDiff(this, d2);
    };
    moment.preciseDiff = function(d1, d2) {
        var m1 = moment(d1), m2 = moment(d2);
        if (m1.isSame(m2)) {
            return STRINGS.nodiff;
        }
        if (m1.isAfter(m2)) {
            var tmp = m1;
            m1 = m2;
            m2 = tmp;
        }
        var yDiff = m2.year() - m1.year();
        var mDiff = m2.month() - m1.month();
        var dDiff = m2.date() - m1.date();
        var hourDiff = m2.hour() - m1.hour();
        var minDiff = m2.minute() - m1.minute();
        var secDiff = m2.second() - m1.second();
        var msecDiff = m2.millisecond() - m1.millisecond();
        if(msecDiff < 0) {
            msecDiff = 1000 + secDiff;
            secDiff--;
        }
        if (secDiff < 0) {
            secDiff = 60 + secDiff;
            minDiff--;
        }
        if (minDiff < 0) {
            minDiff = 60 + minDiff;
            hourDiff--;
        }
        if (hourDiff < 0) {
            hourDiff = 24 + hourDiff;
            dDiff--;
        }
        if (dDiff < 0) {
            var daysInLastFullMonth = moment(m2.year() + '-' + (m2.month() + 1), "YYYY-MM").subtract('months', 1).daysInMonth();
            if (daysInLastFullMonth < m1.date()) { // 31/01 -> 2/03
                dDiff = daysInLastFullMonth + dDiff + (m1.date() - daysInLastFullMonth);
            } else {
                dDiff = daysInLastFullMonth + dDiff;
            }
            mDiff--;
        }
        if (mDiff < 0) {
            mDiff = 12 + mDiff;
            yDiff--;
        }
        function pluralize(num, word) {
            return num + ' ' + STRINGS[word + (num === 1 ? '' : 's')];
        }
        var result = [];
        if (yDiff) {
            result.push(pluralize(yDiff, 'year'));
        }
        if (mDiff) {
            result.push(pluralize(mDiff, 'month'));
        }
        if (dDiff) {
            result.push(pluralize(dDiff, 'day'));
        }
        if (hourDiff) {
            result.push(pluralize(hourDiff, 'hour'));
        }
        if (minDiff) {
            result.push(pluralize(minDiff, 'minute'));
        }
        if (secDiff) {
            result.push(pluralize(secDiff, 'second'));
        }
        if (msecDiff) {
            result.push(pluralize(msecDiff, 'millisecond'));
        }
        return result.join(STRINGS.delimiter);
    };
});

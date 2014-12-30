define(['powa/models/DataSource'], function(DataSource){
    return DataSource.extend({

        update: function(from_date, to_date){
            var self = this;
            $.ajax({
                url: this.getUrl(from_date, to_date),
                type: 'GET',
            }).done(function(response){
                self.trigger("contentsource:dataload", response);
            }).fail(function(response){
                var value = response.status != 500 ? response.responseText: ""
                self.trigger("contentsource:dataload-failed", value);
            });
        }
    }, {
        fromJSON: function(jsonobj){
            return new this(jsonobj);
        }
    });
});

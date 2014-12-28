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
                self.trigger("contentsource:dataload", "An error occured");
            });
        }
    }, {
        fromJSON: function(jsonobj){
            return new this(jsonobj);
        }
    });
});

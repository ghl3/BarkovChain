

console.log("Loading jscript");

/*
GEvent.addListener(map, "click", function(marker,point) {
    var latitude = point.y;
    var longitude = point.x;
    
    console.log(latitude);
    console.log(longitude);
});
*/

var marker = null;

function placeMarker(map, location) {

    // Create if necessary
    if( !marker ){
	marker = new google.maps.Marker({position: location, map: map});
    }

    // Set its position
    marker.setPosition(location);
}

$(document).ready(function() {
    
    console.log("Loading Map");

    var mapOptions = {
	center: new google.maps.LatLng(40.7, -74),
	zoom: 12,
	mapTypeId: google.maps.MapTypeId.ROADMAP
    };

    var map = new google.maps.Map(document.getElementById("map_canvas"),
				  mapOptions);

    google.maps.event.addListener(map, 'click', function(event) {
	placeMarker(map, event.latLng);
	console.log( marker['position']['Ya'] );
	console.log( marker['position']['Za'] );
    });
    
    console.log("Loaded Map");

    /*
    google.maps.event.addListener(map, 'click', function(event) {
        marker = new google.maps.Marker({position: event.latLng, map: map});
	console.log(marker);
	console.log( marker['position']['Ya'] );
	console.log( marker['position']['Za'] );
    });
    */

});

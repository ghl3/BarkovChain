

console.log("Loading jscript");

// Global Variables
var marker = null;
var current_position = {'latitude' : null, 'longitude' : null};

var mapOptions = {
    center: new google.maps.LatLng(40.7, -74),
    zoom: 12,
    mapTypeId: google.maps.MapTypeId.ROADMAP,
    //draggable: false,
    //scrollwheel: false,
    minZoom: 13, maxZoom: 18
};


// Put the marker on the map
// (creating if necessary)
function placeMarker(map, location) {

    if( marker ){
	marker.setMap(null);
	marker = null;
    }

    // Create if necessary
    if( !marker ){
	marker = new google.maps.Marker({
	    position: location, 
	    map: map,
	    animation: google.maps.Animation.DROP
	});
    }
}


// SubmitLocationToServer
function submitLocationToServer() {
    console.log('Submitting Location To Server');

    /*
    var jqxhr = $.getJSON("/api/locations", 
			  {"current_position" : current_position, 
			   "num_locations" : 3})
	.done(function() { console.log("done");})
	.always(function() { console.log("always");})
*/
    
    var data = {"current_position" : current_position, 
		"num_locations" : 3};

    $.ajax({
	url: "/api/locations",
	dataType: 'json',
	contentType:"application/json; charset=utf-8",
	data: data
    })
	.done(function() { console.log("done");})
	.always(function() { console.log("always");})
    


    console.log("Sent request to get locations.  Waiting...");    

    /*
    $.post("/api/locations", {"current_position" : current_position, "num_locations" : 3})
	.done(function() { console.log("done");})
	.always(function() { console.log("always");})
	*/
    
    /*
	   successfulCallback)
	   .error(errorCallback);
    */
    

    

}


// Load the page! 
$(document).ready(function() {
    
    console.log("Loading Map");
    
    // Create the map
    var map = new google.maps.Map(document.getElementById("map_canvas"),
				  mapOptions);

    // Define clicking on the map
    google.maps.event.addListener(map, 'click', function(event) {
	placeMarker(map, event.latLng);
	var lat = marker['position']['Ya'];
	var lon = marker['position']['Za'];
	//console.log(lat);
	//console.log(lon);
	current_position['latitude'] = lat;
	current_position['longitude'] = lon;
	console.log(current_position);
    });
    
    console.log("Loaded Map");

    // Define clicking on the 'submit' button
    // Send an ajax request to the flask server
    // and get some info
    $("#button_create").click(submitLocationToServer);
    
    // Define the submit button
    

});

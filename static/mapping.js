

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


// Clear a table and recreate based
// on the input list of data points
function addDataToTable(data, table_id) {
    console.log("Place holder");
}


// SubmitLocationToServer
function submitLocationToServer() {
    console.log('Submitting Location To Server');

    if( current_position['latitude'] == null ) {
	console.log("Current latitude is null");
	return;
    }
    if( current_position['longitude'] == null ) {
	console.log("Current longitude is null");
	return;
    }

    var data = {"longitude" : current_position['longitude'], 
		"latitude" : current_position['latitude'], 
		"number_of_locations" : 3};

    console.log("Sending data:");
    console.log(data);

    function successfulCallback(data) {

	// Add the data to the table
	addDataToTable(data, "#venue_list");

	console.log(data);
	console.log("Success");
    }
    
    function errorCallback(data) {
	console.log(data);
	console.log("Error");
	
    }

    $.ajax({
	url: "/api/locations",
	dataType: 'json',
	contentType:"application/json; charset=utf-8",
	data: data
    })
	.done(successfulCallback)
	.fail(errorCallback)
	.always(function() { 
	    console.log("Done with 'submitLocationToServer'");
	});
    
    console.log("Sent request to get locations.  Waiting...");    

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


});

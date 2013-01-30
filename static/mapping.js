

console.log("Loading jscript");

// Global Variables
var map = null;
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
function createTableFromData(data, columns) {

    console.log("Place holder");
    
    // Create the Table
    var table = document.createElement('table');
    //table.setAttribute('id', table_id);

    // Add the Title
    var row = table.insertRow(0);

    // Create the header
    for( var column_idx = 0; column_idx < columns.length; ++column_idx ) {
	var cell = row.insertCell(column_idx);
	cell.innerHTML = columns[column_idx];
    }

    // Add the data rows
    for(var data_itr=0; data_itr<data.length; ++data_itr) {
	var dict = data[data_itr];

	// Recall that the header row is row=0
	var row = table.insertRow(data_itr+1);

	for( var column_idx = 0; column_idx < columns.length; ++column_idx ) {
	    var cell = row.insertCell(column_idx);
	    var var_name = columns[column_idx];
	    cell.innerHTML = dict[var_name];
	    cell.className += "table_column_" + column_idx;
	    
	}
    }

    return table;

}


function createPath(data) {

    var coordinates = new Array();

    for(var data_itr=0; data_itr<data.length; ++data_itr) {
	if(data_itr > 3) break;
	var dict = data[data_itr];
	var lat = dict['latitude'];
	var lon = dict['longitude'];
	var position = new google.maps.LatLng(lat, lon);
	coordinates.push(position);
    }

    /*
    var flightPlanCoordinates = [
        new google.maps.LatLng(37.772323, -122.214897),
        new google.maps.LatLng(21.291982, -157.821856),
        new google.maps.LatLng(-18.142599, 178.431),
        new google.maps.LatLng(-27.46758, 153.027892)
    ];
    */
    var flightPath = new google.maps.Polyline({
	path: coordinates,
	strokeColor: "#FF0000",
	strokeOpacity: 1.0,
	strokeWeight: 2
    });

    flightPath.setMap(map);

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
	var table = createTableFromData(data, ["name", "address"]);
	$("#venue_list").append(table);

	// Create a path on the map
	createPath(data);

	console.log("successfulCallback: Table");
	console.log(table);
	//addDataToTable(data, "#venue_list");
	//console.log(data);
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
    //var map = new google.maps.Map(document.getElementById("map_canvas"),
    //				  mapOptions);
    map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);

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

(function() {
  'use strict';
// var controllerID = 'DevicesController';
angular.module('hisraWebapp')

.controller('PlaylistsController', PlaylistController);

/* @ngInject */
function PlaylistController($location, Authentication, User) {
  var vm = this;

  var user = Authentication.getCurrentUser();
  if(user === undefined) {
      return $location.path('/login');
  }
  vm.playlists = [];

  User.getPlaylists({username: user.username}).$promise
    .then(function (playlists) {
      vm.playlists = playlists.map(function(playlist) {
        // JSON parsing doesn't seem to accept single parentheses
        var jsonSchedule = playlist.media_schedule_json;
        playlist.media_schedule = JSON.parse(jsonSchedule);
        return playlist;
      });
    });
}

})();

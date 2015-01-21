'use strict';

/**
 * @ngdoc function
 * @name weberApp.controller:MainCtrl
 * @description
 * # MainCtrl
 * Controller of the weberApp
 */
angular.module('weberApp')
	.controller('MainCtrl', function($scope, $auth, Restangular, InfinitePosts, $alert, $http, CurrentUser, UserService) {
		$scope.UserService = UserService;

		$http.get('/api/me', {
			headers: {
				'Content-Type': 'application/json'
			}
		}).success(function(user_id) {
			Restangular.one('people', user_id).get().then(function(user) {
				$scope.user = user;
				$scope.infinitePosts = new InfinitePosts(user);
				if (user.friends.length !== 0) {
					Restangular.all('people').getList({
						where: {
							"_id": {
								"$in": $scope.user.friends
							}
						}
					}).then(function(friends) {
						$scope.friends = friends;
					});
				}
				$scope.submit_post = function() {
					$scope.infinitePosts.addPost($scope.new_post);
					$scope.new_post = '';
				};
			});
		});
	});
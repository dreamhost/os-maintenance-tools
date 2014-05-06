#!/usr/bin/perl

use Date::Parse;
use strict;

my $count = shift;

my (%api_req_start, %vol_req_start, %vol_req_complete, $api_log_count, $vol_log_count);

open(API, "/var/log/cinder/cinder-api.log");
while (my $api_log = <API>) {
  if ( $api_log =~ /.*AUDIT cinder\.api\.v1\.volumes \[req\-(\S+).+Create volume of/ ) {
    my $stamp = (split(/\s+/, $api_log))[0] . " " . (split(/\s+/, $api_log))[1];
    $api_req_start{$1} = str2time($stamp);
    if ( $count && $api_log_count++ > $count ) {
      last;
    }
  }
}
open(VOLUME, "/var/log/cinder/cinder-volume.log");
while (my $vol_log = <VOLUME>) {
  my $stamp = (split(/\s+/, $vol_log))[0] . " " . (split(/\s+/, $vol_log))[1];
  if ( $vol_log =~ /INFO cinder\.volume\.flows\.create_volume \[req\-(\S+).*being created using CreateVolumeFromSpecTask._create/ ) {
    $vol_req_start{$1} = str2time($stamp); 
    if ( $count && $vol_log_count++ > $count ) {
      last;
    }
  }
  elsif ( $vol_log =~ /INFO cinder\.volume\.flows\.create_volume \[req\-(\S+).*: created successfully/ ) {
    $vol_req_complete{$1} = str2time($stamp);
    if ( $count && $vol_log_count++ > $count ) {
      last;
    }
  }
}

my ($vol_count, $tot_api_to_vol_delta, $tot_vol_complete_delta, $best_api_vol_delta, $worst_api_vol_delta, $best_vol_delta, $worst_vol_delta);
foreach my $request ( keys %api_req_start ) {
  if ( $api_req_start{$request} && $vol_req_start{$request} && $vol_req_complete{$request} ) {
    $vol_count++;
    my $api_vol_delta = $vol_req_start{$request} - $api_req_start{$request};
    $tot_api_to_vol_delta += $api_vol_delta;
    $best_api_vol_delta = $api_vol_delta if $api_vol_delta < $best_api_vol_delta;
    $worst_api_vol_delta = $api_vol_delta if $api_vol_delta > $worst_api_vol_delta;
    my $vol_delta = $vol_req_complete{$request} - $vol_req_start{$request};
    $tot_vol_complete_delta += $vol_delta;
    $best_vol_delta = $vol_delta if $vol_delta < $best_vol_delta;
    $worst_vol_delta = $vol_delta if $vol_delta > $worst_vol_delta;
  }
}
print "best_api_vol_delta = " . sprintf("%.3f", $best_api_vol_delta) . "\n";
print "worst_api_vol_delta = " . sprintf("%.3f", $worst_api_vol_delta) . "\n";
print "best_vol_delta = " . sprintf("%.3f", $best_vol_delta) . "\n";
print "worst_vol_delta = " . sprintf("%.3f", $worst_vol_delta) . "\n";
print "$vol_count tracked requests with average time of " . sprintf("%.3f",($tot_api_to_vol_delta/$vol_count)) . "s from api:volume and " . sprintf("%.3f",($tot_vol_complete_delta/$vol_count)) . "s to vol_complete\n";


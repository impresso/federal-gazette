#!/usr/bin/perl

# create reasonable casing variants
# expects one word by line
use open qw( :encoding(UTF-8) :std );
use feature 'unicode_strings';
%seen = ();
local $\ = "\n"; # print newline after each print statement

while (<>) {
  chomp;
  unless (exists $seen{$_}) {
  	print;
  	$seen{$_}++;
  };

  # only lowercase first character if not all uppercase, avoid wORT
  if ( ! /^\p{Uppercase}+$/ ) {
  	$Lc = lcfirst;
  	unless (exists $seen{$Lc}) {
  		print $Lc;
  		$seen{$Lc}++;
  	};
  };

  $lc = lc;
  unless (exists $seen{$lc}) {
  	print $lc;
  	$seen{$lc}++;
  };
    $Uc = ucfirst $lc;
  unless (exists $seen{$Uc}) {
  	print $Uc;
  	$seen{$Uc}++;
  };

  $uc = uc;
 unless (exists $seen{$uc}) {
   print $uc;
   $seen{$uc}++;
 }; 
}

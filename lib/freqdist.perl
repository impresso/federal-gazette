#!/usr/bin/perl

use open qw( :encoding(UTF-8) :std );

%freq = ();
while (<>) {
  chomp;
  s/[\f\v]//g;
  $freq{$_}++;
  if (s/^.+-([^-]{2,})$/\1/) {
  	$freq{$_}++;
  }
}

foreach my $name (sort { $freq{$b} <=> $freq{$a} } keys %freq) {
    print $freq{$name},"\t", $name,  "\n";
}

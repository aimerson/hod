#! /usr/bin/env python
from __future__ import print_function
import numpy as np
import h5py
import parameters as par
from cosmology import Cosmology
from catalogue import Catalogue


class MXXLCatalogue(Catalogue):
    """
    MXXL halo lightcone catalogue
    """

    def __init__(self, file_name=par.halo_file):

        if file_name is None:
            self._quantities = {}
            self.size = 0

        else:
            # read halo catalogue file
            halo_cat = h5py.File(file_name, "r")

            self._quantities = {
                'ra':    self.__read_property(halo_cat, 'ra'),
                'dec':   self.__read_property(halo_cat, 'dec'),
                'mass':  self.__read_property(halo_cat, 'M200m') * 1e10,
                'zobs':  self.__read_property(halo_cat, 'z_obs'),
                'zcos':  self.__read_property(halo_cat, 'z_cos'),
                'vmax':  self.__read_property(halo_cat, 'vmax'),
                'rvmax': self.__read_property(halo_cat, 'rvmax')
                }
            halo_cat.close()

            self.size = len(self._quantities['ra'][...])


    def __read_property(self, halo_cat, prop):
        # read property from halo file
        return halo_cat["Data/"+prop][...]
    

    def get(self, prop):
        """
        Get property from catalogue

        Args:
            prop: string of the name of the property
        Returns:
            array of property
        """
        # calculate properties not directly stored
        if prop == "log_mass":
            return np.log10(self._quantities["mass"])
        elif prop == "r200":
            return self.get_r200()
        elif prop == "conc":
            return self.get_concentration()
        elif prop == "mod_conc":
            return self.get_modified_concentration()
        
        # property directly stored
        return self._quantities[prop]


    def get_r200(self, comoving=True):
        """
        Returns R200mean of each halo

        Args:
            comoving: (optional) if True convert to comoving distance
        Returns:
            array of R200mean [Mpc/h]
        """
        cosmo = Cosmology(par.h0, par.OmegaM, par.OmegaL)
        rho_mean = cosmo.mean_density(self.get("zcos"))
        r200 = (3./(800*np.pi) * self.get("mass") / rho_mean)**(1./3)
        
        if comoving:
            return r200 * (1.+self.get("zcos"))
        else:
            return r200
    

    def get_concentration(self):
        """
        Returns NFW concentration of each halo, calculated from
        R200 and RVmax

        Returns:
            array of halo concentrations
        """
        conc = 2.16 * self.get("r200") / self.get("rvmax")

        return np.clip(conc, 0.1, 1e4)


    def get_modified_concentration(self):
        """
        Returns NFW concentration of each halo, modified to
        produce the right small scale clustering 
        (see Smith et al 2017)

        Returns:
            array of halo concentrations
        """
        # concentration from R200 and RVmax
        conc = self.get_concentration()
        conc_mod = np.zeros(len(conc))

        # mass bins
        mass_bins = np.arange(10, 16, 0.01)
        mass_bin_cen = mass_bins[:-1]+ 0.005
        logc_neto_mean = np.log10(4.67) - 0.11*(mass_bin_cen - 14)

        log_mass = self.get("log_mass")
        # loop through mass bins
        for i in range(len(mass_bins)-1):
            ind = np.where(np.logical_and(log_mass >= mass_bins[i], 
                                          log_mass < mass_bins[i+1]))[0]
            
            # for haloes in mass bin, randomly generate new concentration
            # from Neto conc-mass relation
            # sort old and new concentrations from min to max
            # replace with new concentrations

            logc_new = np.random.normal(loc=logc_neto_mean[i], scale=0.1,
                                        size=len(ind))

            conc_mod[ind[np.argsort(conc[ind])]] = 10**np.sort(logc_new)

        return conc_mod



if __name__ == "__main__":
    cat = MXXLCatalogue()
    print(cat.get("mod_conc"))

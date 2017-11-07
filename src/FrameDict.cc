/*
 * LSST Data Management System
 * Copyright 2017 AURA/LSST.
 *
 * This product includes software developed by the
 * LSST Project (http://www.lsst.org/).
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the LSST License Statement and
 * the GNU General Public License along with this program.  If not,
 * see <https://www.lsstcorp.org/LegalNotices/>.
 */
#include <cassert>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

#include "astshim/FrameDict.h"

namespace ast {

void FrameDict::addFrame(int iframe, Mapping const &map, Frame const &frame) {
    if (hasDomain(frame.getDomain())) {
        throw std::invalid_argument("A frame already exists with domain " + frame.getDomain());
    }
    FrameSet::addFrame(iframe, map, frame);
    _addFrameToDict(frame, FrameSet::getCurrent(), true);
}

void FrameDict::addFrame(std::string const &domain, Mapping const &map, Frame const &frame) {
    addFrame(getIndex(domain), map, frame);
}

std::set<std::string> FrameDict::getAllDomains() const {
    std::set<std::string> domains;
    for (auto const &item : _domainIndexDict) {
        domains.emplace(item.first);
    }
    return domains;
}

void FrameDict::setDomain(std::string const &domain) {
    if (getDomain() == domain) {
        // null rename
        return;
    }
    if (hasDomain(domain)) {
        throw std::invalid_argument("Another framea already has domain name " + domain);
    }
    Frame::setDomain(domain);
    _rebuildDict(true);
}

FrameDict::FrameDict(AstFrameSet *rawptr) : FrameSet(rawptr) {
    if (!astIsAFrameSet(getRawPtr())) {
        std::ostringstream os;
        os << "this is a " << getClassName() << ", which is not a FrameSet";
        throw std::invalid_argument(os.str());
    }
    _rebuildDict(false);
}

}  // namespace ast

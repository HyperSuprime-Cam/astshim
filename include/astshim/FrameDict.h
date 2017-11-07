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
#ifndef ASTSHIM_FRAMEDICT_H
#define ASTSHIM_FRAMEDICT_H

#include <cassert>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

#include "astshim/base.h"
#include "astshim/detail/utils.h"
#include "astshim/Frame.h"
#include "astshim/FrameSet.h"

namespace ast {

/**
A FrameSet whose frames can be referenced by domain name.

For every FrameSet method that takes a frame index, the same method in FrameDict may take a (case blind)
domain name or a frame index.

This has several useful applications:
- Locate a frame without changing the FrameSet (findFrame is not a const method).
- Locate a frame or mapping in a way that is unaffected by deleting frames
  (indices change, domain names do not).

All contained Frames with explicitly set, non-empty domains must have unique domains (where the comparison
ignores case). Use FrameSet if you want a collection of Frames that may have matching domains.

@warning FrameDict.getClassName returns "FrameSet". This is because FrameDict has no direct AST equivalent;
it is merely a convenience wrapper around FrameSet.

@note
- AST casts all Frame domains to uppercase. This is why domain comparison and domain lookup are case blind.
- Some AST frame classes have default domain names, e.g. SkyFrame defaults to "SKY". Such default
names are ignored in order to reduce the chance of accidental collisions.

### Attributes

All those of FrameSet.
*/
class FrameDict : public FrameSet {
    friend class Object;

public:
    /**
    Construct a FrameDict from a single Frame

    The frame is deep copied.

    @param[in] frame  the first @ref Frame to be inserted into the @ref FrameDict.
                    This initially becomes both the base and the current Frame.
                    Further Frames may be added using @ref addFrame
    @param[in] options  Comma-separated list of attribute assignments.
    */
    explicit FrameDict(Frame const &frame, std::string const &options = "") : FrameSet(frame, options) {
        _rebuildDict(false);
    }

    /**
    Construct a FrameDict from two frames and a mapping that connects them

    Both frames and the mapping are deep copied.

    @param[in] baseFrame  base @ref Frame.
    @param[in] mapping  mapping connecting baseFrame to currentFrame.
    @param[in] currentFrame  current @ref Frame.
    @param[in] options  Comma-separated list of attribute assignments.

    @throws std::invalid_argument if both Frames have the same non-empty domain.
    */
    explicit FrameDict(Frame const &baseFrame, Mapping const &mapping, Frame const &currentFrame,
                       std::string const &options = "")
            : FrameSet(baseFrame, mapping, currentFrame) {
        _rebuildDict(false);
    }

    /**
    Construct a FrameDict from a FrameSet

    The FrameSet is deep-copied

    @throws std::invalid_argument if two Frames in the FrameSet have the same non-empty domain.
    */
    explicit FrameDict(FrameSet const &frameSet)
            : FrameDict(reinterpret_cast<AstFrameSet *>(frameSet.copy()->getRawPtr())) {}
    virtual ~FrameDict() {}

    FrameDict(FrameDict const &) = delete;
    FrameDict(FrameDict &&) = default;
    FrameDict &operator=(FrameDict const &) = delete;
    FrameDict &operator=(FrameDict &&) = default;

    /// Return a deep copy of this object.
    std::shared_ptr<FrameDict> copy() const { return std::static_pointer_cast<FrameDict>(copyPolymorphic()); }

    /**
    @copydoc FrameSet::addFrame

    @throws std::invalid_argument if `frame` has a non-empty domain and this FrameDict already
    contains a Frame with that domain
    */
    void addFrame(int iframe, Mapping const &map, Frame const &frame) override;

    /**
    Variant of @ref addFrame(int, Mapping const &, Frame const &) "addFrame(int, ...)"
    where the initial frame is specified by domain.
    */
    void addFrame(std::string const &domain, Mapping const &map, Frame const &frame);

    /**
    Get the domain names for all contained Frames (excluding frames with empty or defaulted domain names).
    */
    std::set<std::string> getAllDomains() const;

    using FrameSet::getFrame;

    /**
    Variant of @ref FrameSet::getFrame "getFrame(int, bool)" where the frame
    is specified by domain name.

    @throw std::out_of_range if no frame found with the specified domain
    */
    std::shared_ptr<Frame> getFrame(std::string const &domain, bool copy = true) const {
        return FrameSet::getFrame(getIndex(domain), copy);
    }

    using FrameSet::getMapping;

    /**
    Variant of @ref FrameSet::getMapping(int, int) "getMapping(int, int)"
    with the second frame specified by domain.

    @throw std::out_of_range if no frame found with the specified from or to domain
    */
    std::shared_ptr<Mapping> getMapping(int from, std::string const &to) const {
        return FrameSet::getMapping(from, getIndex(to));
    }

    /**
    Variant of @ref FrameSet::getMapping(int, int) "getMapping(int, int)"
    with the first frame specified by domain.

    @throw std::out_of_range if no frame found with the specified from or to domain
    */
    std::shared_ptr<Mapping> getMapping(std::string const &from, int to) const {
        return FrameSet::getMapping(getIndex(from), to);
    }

    /**
    Variant of @ref FrameSet::getMapping(int, int) "getMapping(int, int)"
    with the both frames specified by domain.

    @throw std::out_of_range if no frame found with the specified from or to domain
    */
    std::shared_ptr<Mapping> getMapping(std::string const &from, std::string const &to) const {
        return FrameSet::getMapping(getIndex(from), getIndex(to));
    }

    /**
    Get the index of a frame specified by domain

    @throw std::out_of_range if no frame found with the specified domain
    */
    int getIndex(std::string const &domain) const {
        auto domainUpper = detail::stringToUpper(domain);
        auto it = _domainIndexDict.find(domainUpper);
        if (it == _domainIndexDict.end()) {
            throw std::out_of_range("No frame found with domain " + domain);
        }
        return it->second;
    }

    /**
    Return True if a frame in this FrameDict has the specified domain
    */
    bool hasDomain(std::string const &domain) const { return _domainIndexDict.count(domain) > 0; }

    using FrameSet::mirrorVariants;

    /**
    Variant of @ref FrameSet::mirrorVariants(int) "mirrorVariants(int)" with the frame specified by domain

    @throw std::out_of_range if no frame found with the specified domain
    */
    void mirrorVariants(std::string const &domain) { FrameSet::mirrorVariants(getIndex(domain)); }

    using FrameSet::remapFrame;

    /**
    Variant of @ref FrameSet::remapFrame(int, Mapping&) "remapFrame(int, ...)" with the frame
    specified by domain

    @throw std::out_of_range if no frame found with the specified domain
    */
    void remapFrame(std::string const &domain, Mapping &map) { FrameSet::remapFrame(getIndex(domain), map); }

    using FrameSet::removeFrame;

    /**
    Variant of @ref FrameSet::removeFrame(int) "removeFrame(int)" with the frame specified by domain

    @throw std::out_of_range if no frame found with the specified domain
    */
    void removeFrame(std::string const &domain) {
        FrameSet::removeFrame(getIndex(domain));
        _rebuildDict(true);
    }

    using FrameSet::setBase;

    /**
    Variant of @ref FrameSet::setBase(int) "setBase(int)" with the frame specified by domain

    @throw std::out_of_range if no frame found with the specified domain
    */
    void setBase(std::string const &domain) { FrameSet::setBase(getIndex(domain)); }

    using FrameSet::setCurrent;

    /**
    Variant of @ref FrameSet::setCurrent(int) "setCurrent(int)" with the frame specified by domain

    @throw std::out_of_range if no frame found with the specified domain
    */
    void setCurrent(std::string const &domain) { FrameSet::setCurrent(getIndex(domain)); }

    /**
    Set the domain of the current frame (and update the internal dict).

    @throws std::invalid_argument if another frame already has this domain
    */
    void setDomain(std::string const &domain) override;

protected:
    virtual std::shared_ptr<Object> copyPolymorphic() const override {
        return copyImpl<FrameDict, AstFrameSet>();
    }

    /// Construct a FrameDict from a raw AST pointer
    explicit FrameDict(AstFrameSet *rawptr);

private:
    /*
    Rebuild the internal domain:index dictionary

    @param[in] doAssert  If a Frame already exists with this domain then assert if true,
                        else throw std::invalid_argument. False is only appropriate for constructors.
    */
    void _rebuildDict(bool doAssert) {
        _domainIndexDict.clear();
        for (int index = 1, end = getNFrame(); index <= end; ++index) {
            auto const frame = FrameSet::getFrame(index, false);
            _addFrameToDict(*frame, index, doAssert);
        }
    }

    /*
    Add one frame to the internal domain:index dictionary

    Silently do nothing if the frame has a defaulted domain (e.g. SkyFrame defaults to "SKY")
    or an empty domain.

    @param[in] frame  Frame to add to dictionary
    @param[in] index  Index of frame in FrameSet
    @param[in] doAssert  If a Frame already exists with this domain then assert if true,
                        else throw std::invalid_argument. False is only appropriate for constructors.
    */
    void _addFrameToDict(Frame const &frame, int index, bool doAssert) {
        if (frame.test("Domain")) {
            auto domain = frame.getDomain();
            if (domain.empty()) {
                return;
            }
            if (doAssert) {
                assert(!hasDomain(domain));
            } else if (hasDomain(domain)) {
                throw std::invalid_argument("More than one frame with domain " + domain);
            }
            _domainIndexDict[domain] = index;
        }
    }

    std::unordered_map<std::string, int> _domainIndexDict;  // Dict of frame domain:index
};

}  // namespace ast

#endif
